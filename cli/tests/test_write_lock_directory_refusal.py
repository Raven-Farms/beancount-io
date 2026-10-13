"""An unusable lock directory refuses the write as a permission failure (w5/113).

Writers lock under `$XDG_CACHE_HOME/bea/locks`. When that directory could not
be created or opened, `add` and `format -i` failed with a raw `PermissionError`
/ `NotADirectoryError` / `FileExistsError` reported as validation (exit 1),
the code that means the ledger is broken.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    sys.platform == "win32" or os.geteuid() == 0, reason="needs POSIX permissions that bind this user"
)

LEDGER = "2024-01-01 open Assets:Cash   USD\n2024-01-01 open Expenses:Food USD\n"
ADD = ("add", "transaction", "N", "--date", "2024-02-01", "-p", "Expenses:Food 5.00 USD", "-p", "Assets:Cash")
ADD_OPEN = ("add", "open", "--account", "Assets:New", "--date", "2024-01-01")
EXCEPTION_NAMES = ("PermissionError", "NotADirectoryError", "FileExistsError", "Errno", "--debug")


def _read_only_root(tmp_path: Path) -> Path:
    cache = tmp_path / "ro"
    cache.mkdir()
    cache.chmod(0o555)
    return cache


def _root_is_a_file(tmp_path: Path) -> Path:
    cache = tmp_path / "cache-file"
    cache.write_text("")
    return cache


def _locks_is_a_file(tmp_path: Path) -> Path:
    cache = tmp_path / "cache"
    (cache / "bea").mkdir(parents=True)
    (cache / "bea" / "locks").write_text("")
    return cache


CACHES = [_read_only_root, _root_is_a_file, _locks_is_a_file]


def _bea(tmp_path: Path, cache: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(cache),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def _ledger(tmp_path: Path) -> Path:
    ledger = tmp_path / "books" / "main.bean"
    ledger.parent.mkdir()
    ledger.write_text(LEDGER)
    return ledger


def _restore(cache: Path) -> None:
    """Let pytest remove the read-only root afterwards."""
    if cache.is_dir():
        cache.chmod(0o755)


def _assert_refusal(message: str, cache: Path) -> None:
    assert str(cache / "bea" / "locks") in message
    assert "XDG_CACHE_HOME" in message
    assert "Nothing was written" in message
    for name in EXCEPTION_NAMES:
        assert name not in message


@pytest.mark.parametrize("make_cache", CACHES)
@pytest.mark.parametrize("command", [ADD, ("format", "-i")], ids=["add", "format-in-place"])
def test_an_unusable_lock_directory_is_a_permission_refusal(
    tmp_path: Path, make_cache: Callable[[Path], Path], command: tuple[str, ...]
) -> None:
    ledger = _ledger(tmp_path)
    cache = make_cache(tmp_path)
    try:
        result = _bea(tmp_path, cache, "-f", str(ledger), *command)
        check = _bea(tmp_path, cache, "-f", str(ledger), "check")
    finally:
        _restore(cache)

    assert result.returncode == 3, result.stderr
    assert result.stdout == ""
    _assert_refusal(result.stderr, cache)
    assert ledger.read_text() == LEDGER
    # Reads take no lock, so the same cache never blocks them.
    assert check.returncode == 0, check.stderr


@pytest.mark.parametrize("make_cache", CACHES)
def test_the_refusal_keeps_its_category_in_json(tmp_path: Path, make_cache: Callable[[Path], Path]) -> None:
    ledger = _ledger(tmp_path)
    cache = make_cache(tmp_path)
    try:
        result = _bea(tmp_path, cache, "--json", "-f", str(ledger), *ADD_OPEN)
    finally:
        _restore(cache)

    assert result.returncode == 3, result.stderr
    error = json.loads(result.stderr)["error"]
    assert (error["category"], error["exit_code"]) == ("auth", 3)
    _assert_refusal(error["message"], cache)
    assert ledger.read_text() == LEDGER


def test_a_writable_cache_still_writes(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)

    result = _bea(tmp_path, tmp_path / "cache", "-f", str(ledger), *ADD)

    assert result.returncode == 0, result.stderr
    assert "Expenses:Food 5.00 USD" in " ".join(ledger.read_text().removeprefix(LEDGER).split())
    assert list((tmp_path / "cache" / "bea" / "locks").glob("*.lock"))
