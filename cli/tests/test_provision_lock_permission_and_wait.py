"""First-use provisioning fails loud on an unwritable home and waits loud on a held lock (w5/787).

An unwritable data directory was a raw `[Errno 13]` with exit 1; it is now
exit 3 naming the directory and the variable to set. A command queuing
behind another bea's install waited forever in silence; it now prints a
notice after a second (silent under `--json`) and gives up after 60, like
the write lock.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = "2026-01-01 open Assets:Cash USD\n"
INSTALLED_CONTEXT = (
    "from pathlib import Path\nfrom cli.engine import paths\n"
    "paths.checkout_source_root = lambda: None\n"
    f"paths.helper_source_root = lambda: Path({str(ROOT / 'src')!r})\n"
)
REQUIRES_POSIX_PERMISSIONS = pytest.mark.skipif(
    os.name != "posix" or os.geteuid() == 0, reason="requires POSIX permissions binding the current user"
)


def _env(directory: Path) -> dict[str, str]:
    (directory / "main.bean").write_text(LEDGER)
    bootstrap = directory / "bootstrap"
    bootstrap.mkdir(exist_ok=True)
    (bootstrap / "sitecustomize.py").write_text(INSTALLED_CONTEXT)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(directory / "config"),
        XDG_CACHE_HOME=str(directory / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=os.pathsep.join([str(bootstrap), str(ROOT / "src")]),
        TERM="dumb",
        NO_COLOR="1",
    )
    return env


def _bea(directory: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=directory,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@REQUIRES_POSIX_PERMISSIONS
def test_unwritable_data_dir_exits_3_naming_directory_and_variable(tmp_path: Path) -> None:
    rodata = tmp_path / "rodata"
    rodata.mkdir()
    rodata.chmod(0o555)
    try:
        env = _env(tmp_path)
        env["XDG_DATA_HOME"] = str(rodata)
        result = _bea(tmp_path, env, "-f", "main.bean", "check")
    finally:
        rodata.chmod(0o755)

    assert result.returncode == 3, result.stdout + result.stderr
    assert str(rodata / "bea" / "engine") in result.stderr
    assert "XDG_DATA_HOME" in result.stderr
    assert "Permission denied" in result.stderr


@REQUIRES_POSIX_PERMISSIONS
def test_engine_dir_under_readonly_parent_names_bea_engine_dir(tmp_path: Path) -> None:
    rodata = tmp_path / "rodata"
    rodata.mkdir()
    rodata.chmod(0o555)
    try:
        env = _env(tmp_path)
        env["XDG_DATA_HOME"] = str(tmp_path / "data")
        env["BEA_ENGINE_DIR"] = str(rodata / "engine")
        result = _bea(tmp_path, env, "-f", "main.bean", "check")
    finally:
        rodata.chmod(0o755)

    assert result.returncode == 3, result.stdout + result.stderr
    assert "BEA_ENGINE_DIR" in result.stderr


@REQUIRES_POSIX_PERMISSIONS
def test_unwritable_data_dir_json_envelope_is_auth(tmp_path: Path) -> None:
    rodata = tmp_path / "rodata"
    rodata.mkdir()
    rodata.chmod(0o555)
    try:
        env = _env(tmp_path)
        env["XDG_DATA_HOME"] = str(rodata)
        result = _bea(tmp_path, env, "--json", "-f", "main.bean", "check")
    finally:
        rodata.chmod(0o755)

    assert result.returncode == 3, result.stdout + result.stderr
    error = json.loads(result.stderr)["error"]
    assert error["category"] == "auth" and error["exit_code"] == 3


_HOLDER = (
    "import sys, time\n"
    "sys.path.insert(0, {src!r})\n"
    "from pathlib import Path\n"
    "from cli.engine.provision import provisioning_lock\n"
    "with provisioning_lock(Path(sys.argv[1])):\n"
    "    print('READY', flush=True)\n"
    "    time.sleep(30)\n"
)


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_waiting_notices_promptly_and_stays_silent_as_json(tmp_path: Path, as_json: bool) -> None:
    env = _env(tmp_path)
    engine = tmp_path / "managed" / "engine"
    env["BEA_ENGINE_DIR"] = str(engine)
    holder = subprocess.Popen(
        [sys.executable, "-c", _HOLDER.format(src=str(ROOT / "src")), str(engine)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        text=True,
    )
    assert holder.stdout is not None and holder.stdout.readline().strip() == "READY"
    args = ["--json", "-f", "main.bean", "check"] if as_json else ["-f", "main.bean", "check"]
    waiter = subprocess.Popen(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    try:
        time.sleep(2.5)
        assert waiter.poll() is None, "bea left the held lock instead of waiting"
        waiter.kill()
        _, stderr = waiter.communicate(timeout=15)
    finally:
        holder.kill()
        holder.wait(timeout=15)
        if waiter.poll() is None:
            waiter.kill()
            waiter.communicate(timeout=15)

    if as_json:
        assert "Waiting up to" not in stderr
    else:
        assert "Waiting up to 60 seconds for another bea to finish installing the engine" in stderr
        assert str(engine) in stderr


def test_waiting_gives_up_after_the_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from cli.engine import provision
    from cli.errors import ConflictError

    root = tmp_path / "managed" / "engine"
    monkeypatch.setattr(provision, "_PROVISION_LOCK_TIMEOUT", 0.3)
    entered = threading.Event()
    release = threading.Event()

    def hold() -> None:
        with provision.provisioning_lock(root):
            entered.set()
            assert release.wait(timeout=30)

    worker = threading.Thread(target=hold, daemon=True)
    worker.start()
    assert entered.wait(timeout=30)
    try:
        with pytest.raises(ConflictError, match="another bea") as caught:
            with provision.provisioning_lock(root):
                pass
    finally:
        release.set()
        worker.join(timeout=30)

    assert str(root) in str(caught.value)
    assert "Retry once that install has finished" in str(caught.value)
