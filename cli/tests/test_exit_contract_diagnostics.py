"""Staging, captured signals and price-status validity use the exit contract (w5/680)."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from cli.engine import launch
from cli.errors import BeaError

ROOT = Path(__file__).resolve().parents[1]
LEDGER = "2026-01-01 open Assets:Checking USD\n2026-01-01 open Expenses:Food USD\n"


def _bea(tmp_path: Path, *args: str, engine: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("BEA_") and key != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
        TERM="dumb",
    )
    if engine is not None:
        env["BEA_ENGINE_PYTHON"] = str(engine)
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", *args],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
    )


def _import(tmp_path: Path, *, apply: bool, as_json: bool) -> tuple[Path, Path, list[str]]:
    root = tmp_path / "main.bean"
    root.write_text(LEDGER + 'include "txns/*.bean"\n')
    directory = tmp_path / "txns"
    directory.mkdir()
    (directory / "a.bean").write_text("")
    source = tmp_path / "s.csv"
    source.write_text("Date,Description,Amount\n2026-02-01,Lunch,-12\n")
    args = [
        *(["--json"] if as_json else []),
        "--file",
        str(root),
        "import",
        str(source),
        "--account",
        "Assets:Checking",
        "--default-account",
        "Expenses:Food",
        "--into",
        "txns/new.bean",
        *(["--apply"] if apply else []),
    ]
    return root, directory, args


@pytest.mark.skipif(sys.platform == "win32" or os.geteuid() == 0, reason="requires binding POSIX directory modes")
@pytest.mark.parametrize("as_json", [False, True], ids=["text", "json"])
@pytest.mark.parametrize("apply", [False, True], ids=["preview", "apply"])
def test_new_import_member_in_read_only_directory_has_no_managed_price_blame(
    tmp_path: Path, apply: bool, as_json: bool
) -> None:
    root, directory, args = _import(tmp_path, apply=apply, as_json=as_json)
    before = root.read_bytes()
    directory.chmod(0o555)
    try:
        result = _bea(tmp_path, *args)
    finally:
        directory.chmod(0o755)

    assert result.returncode == 3, result.stdout + result.stderr
    message = json.loads(result.stderr)["error"]["message"] if as_json else result.stderr
    assert str(directory) in message and "not writable" in message
    assert "managed price" not in message and "price export" not in message
    assert "Nothing was changed" in message
    if as_json:
        assert json.loads(result.stderr)["error"]["category"] == "auth"
    assert root.read_bytes() == before
    assert (directory / "a.bean").read_bytes() == b""
    assert not (directory / "new.bean").exists()
    assert not list(tmp_path.rglob(".bea-*.tmp"))


@pytest.mark.parametrize("apply", [False, True], ids=["preview", "apply"])
def test_new_import_member_still_works_in_a_writable_directory(tmp_path: Path, apply: bool) -> None:
    root, directory, args = _import(tmp_path, apply=apply, as_json=True)
    before = root.read_bytes()

    result = _bea(tmp_path, *args)

    assert result.returncode == 0, result.stdout + result.stderr
    assert root.read_bytes() == before
    destination = directory / "new.bean"
    assert destination.exists() is apply
    if apply:
        assert '"Lunch"' in destination.read_text()
        assert "Assets:Checking" in destination.read_text()
    assert not list(tmp_path.rglob(".bea-*.tmp"))


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signal semantics")
@pytest.mark.parametrize("command", ["example", "treeify"])
@pytest.mark.parametrize(("name", "expected"), [("SIGSEGV", 1), ("SIGTERM", 1), ("SIGINT", 130), ("SIGPIPE", 141)])
def test_captured_native_signal_is_named_or_keeps_its_quiet_shell_status(
    tmp_path: Path, command: str, name: str, expected: int
) -> None:
    binary = tmp_path / "engine" / "bin"
    binary.mkdir(parents=True)
    python = binary / "python3"
    python.symlink_to(sys.executable)
    native = binary / ("bean-example" if command == "example" else "treeify")
    native.write_text(
        f"#!{sys.executable}\nimport os,signal\n"
        "signal.signal(signal.SIGPIPE,signal.SIG_DFL)\n"
        "signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGINT})\n"
        f"os.kill(os.getpid(),signal.{name})\n"
    )
    native.chmod(0o755)
    destination = tmp_path / "export.bean"
    destination.write_bytes(b"LAST GOOD EXPORT\n")
    args = [command, "--force", "-o", str(destination)]

    result = _bea(tmp_path, *args, engine=python)

    assert result.returncode == expected, result.stdout + result.stderr
    assert result.stdout == ""
    assert destination.read_bytes() == b"LAST GOOD EXPORT\n"
    if expected == 1:
        assert f"was killed by {name}" in result.stderr
        assert "exit -" not in result.stderr
        assert "No diagnostic" not in result.stderr
    else:
        assert result.stderr == ""


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signal semantics")
def test_signal_diagnostic_preserves_a_callers_result() -> None:
    completed = subprocess.CompletedProcess(["treeify"], -int(signal.SIGTERM), "", "")
    progress = {"written": []}

    with pytest.raises(BeaError) as caught:
        launch.check_native(completed, "treeify", result=progress)

    assert "SIGTERM" in str(caught.value)
    assert caught.value.result == progress


@pytest.mark.parametrize("state", ["clean", "failed-balance", "missing-source"])
def test_price_status_json_carries_the_complete_ledger_validity(tmp_path: Path, state: str) -> None:
    root = tmp_path / "main.bean"
    extra = {
        "clean": "",
        "failed-balance": "2026-02-01 balance Assets:Checking 9 USD\n",
        "missing-source": 'include "https://beancount.io/prices/BTC-USD"\n',
    }[state]
    root.write_text(LEDGER + extra)
    before = root.read_bytes()

    result = _bea(tmp_path, "--offline", "--json", "--file", str(root), "price", "status")

    assert result.returncode == 0, result.stdout + result.stderr
    envelope = json.loads(result.stdout)
    assert envelope["ledger_valid"] is (state == "clean")
    errors = envelope["ledger_errors"]
    assert bool(errors) is (state != "clean")
    if state == "failed-balance":
        assert any(f"{root}:3: Balance failed" in error for error in errors)
    elif state == "missing-source":
        assert any("no cached revision" in error for error in errors)
        assert envelope["data"]["sources"][0]["freshness"] == "unavailable"
        assert "Run bea price status" not in result.stderr
    assert root.read_bytes() == before
