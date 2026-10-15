"""`price export` into a place the filesystem refuses is exit 3, not a raw OS error (w5/279).

The export created its directories and copied its files with no `OSError`
handling, so a read-only destination printed `PermissionError: [Errno 13]`
and exited 1 — the validation category — where every other command with an
output destination reports a permission failure. `example -o`, named by the
same rule, is pinned beside it.
"""

from __future__ import annotations

import errno
import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

MAIN = 'include "sub/accounts.bean"\n'
ACCOUNTS = "2026-01-01 open Assets:Cash USD\n"
KEEP = b"KEEP EXISTING FILE\n"

needs_permissions = pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="needs POSIX permissions that bind the current user",
)


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.fixture
def source(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    (root / "sub").mkdir(parents=True)
    (root / "main.bean").write_text(MAIN, encoding="utf-8")
    (root / "sub" / "accounts.bean").write_text(ACCOUNTS, encoding="utf-8")
    return root / "main.bean"


@pytest.fixture
def lock(tmp_path: Path) -> Iterator[Path]:
    """A directory the current user may read but not write."""
    directory = tmp_path / "lock"
    directory.mkdir()
    directory.chmod(0o555)
    yield directory
    directory.chmod(0o755)


def _listing(directory: Path) -> dict[str, bytes | None]:
    """Every path under a directory, with file bytes — a refusal changes neither."""
    return {
        str(path.relative_to(directory)): path.read_bytes() if path.is_file() else None
        for path in sorted(directory.rglob("*"))
    }


def _export(tmp_path: Path, ledger: Path, *args: str, as_json: bool = False) -> subprocess.CompletedProcess[str]:
    mode = ("--json",) if as_json else ()
    return _bea(tmp_path, *mode, "--offline", "--file", str(ledger), "price", "export", *args)


def _refusal(result: subprocess.CompletedProcess[str], as_json: bool) -> str:
    """The message of an exit 3 refusal, free of any raw exception text."""
    assert result.returncode == 3, result.stderr or result.stdout
    assert result.stdout == ""
    if as_json:
        error = json.loads(result.stderr)["error"]
        assert (error["category"], error["exit_code"]) == ("auth", 3)
        message = str(error["message"])
    else:
        message = " ".join(result.stderr.split())
    for raw in ("Errno", "PermissionError", "Traceback", "--debug"):
        assert raw not in message, message
    assert "Nothing was written" in message
    return message


@needs_permissions
@pytest.mark.parametrize("as_json", [False, True], ids=["text", "json"])
@pytest.mark.parametrize("below", ["exp", "deep/er/exp"], ids=["child", "nested"])
def test_a_read_only_directory_refuses_the_export_by_name(
    tmp_path: Path, source: Path, lock: Path, as_json: bool, below: str
) -> None:
    result = _export(tmp_path, source, "--output", f"lock/{below}", as_json=as_json)

    assert str(lock.resolve()) in _refusal(result, as_json)
    assert _listing(lock) == {}


@needs_permissions
def test_a_read_only_subdirectory_is_found_before_the_root_is_copied(tmp_path: Path, source: Path) -> None:
    """The root's directory is writable and the include's is not: neither is written."""
    output = tmp_path / "output"
    (output / "sub").mkdir(parents=True)
    (output / "sub").chmod(0o555)
    try:
        result = _export(tmp_path, source, "--output", str(output), as_json=True)

        assert str((output / "sub").resolve()) in _refusal(result, as_json=True)
        assert _listing(output) == {"sub": None}
    finally:
        (output / "sub").chmod(0o755)


@needs_permissions
def test_force_does_not_replace_a_read_only_file(tmp_path: Path, source: Path) -> None:
    output = tmp_path / "output"
    (output / "sub").mkdir(parents=True)
    (output / "sub" / "accounts.bean").write_bytes(KEEP)
    (output / "sub" / "accounts.bean").chmod(0o444)
    before = _listing(output)

    result = _export(tmp_path, source, "--output", str(output), "--force", as_json=True)

    assert str(output / "sub" / "accounts.bean") in _refusal(result, as_json=True)
    assert _listing(output) == before


@needs_permissions
def test_example_into_a_read_only_directory_is_the_same_refusal(tmp_path: Path, lock: Path) -> None:
    result = _bea(tmp_path, "example", "-s", "1", "-o", "lock/ex.beancount")

    message = _refusal(result, as_json=False)
    assert "lock/ex.beancount" in message
    assert str(lock.resolve()) in message
    assert _listing(lock) == {}


def test_a_write_that_fails_midway_names_what_was_already_written(
    tmp_path: Path, source: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """What no check can foresee — a disk filling up — still reports how far it got."""
    from bea_engine import managed_load
    from bea_engine.protocol import EngineError

    rewrite = managed_load._rewrite_export_includes
    calls: list[Path] = []

    def fill_the_disk(original: bytes, path: Path, *rest: object) -> bytes:
        calls.append(path)
        if len(calls) > 1:
            raise OSError(errno.ENOSPC, "No space left on device")
        return rewrite(original, path, *rest)  # type: ignore[arg-type]

    monkeypatch.setattr(managed_load, "_rewrite_export_includes", fill_the_disk)
    output = tmp_path / "output"

    with pytest.raises(EngineError) as caught:
        managed_load.export_portable(source, output, offline=True, root=tmp_path / "cache")

    message = str(caught.value)
    assert caught.value.exit_code == 1
    assert "No space left on device" in message
    assert "1 of 2 files were already written" in message
    assert str(output / "main.bean") in message
    assert "Nothing was written" not in message
    # The include's directory is created only once its content exists (w5/316),
    # so the failed rewrite leaves no empty `sub/` behind.
    assert set(_listing(output)) == {"main.bean"}


def test_a_writable_destination_still_exports_a_ledger_that_checks(tmp_path: Path, source: Path) -> None:
    output = tmp_path / "okdir" / "exp"
    (tmp_path / "okdir").mkdir()

    result = _export(tmp_path, source, "--output", "okdir/exp", as_json=True)

    assert result.returncode == 0, result.stderr or result.stdout
    assert set(_listing(output)) == {"main.bean", "sub", "sub/accounts.bean"}
    check = _bea(tmp_path, "--json", "--file", str(output / "main.bean"), "check")
    assert check.returncode == 0, check.stderr or check.stdout

    # A snapshot whose files are writable is still what --force replaces.
    again = _export(tmp_path, source, "--output", "okdir/exp", "--force", as_json=True)
    assert again.returncode == 0, again.stderr or again.stdout
