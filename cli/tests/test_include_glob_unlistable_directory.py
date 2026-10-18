"""Include globs must report directories they need to list but cannot read (w5/708)."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
READS = [
    pytest.param(("check",), id="check"),
    pytest.param(("balance", "Assets"), id="balance"),
    pytest.param(("balance", "Assets", "--allow-errors"), id="balance-allow-errors"),
    pytest.param(("query", "SELECT account, sum(position) GROUP BY account"), id="query"),
    pytest.param(
        ("query", "SELECT account, sum(position) GROUP BY account", "--allow-errors"), id="query-allow-errors"
    ),
    pytest.param(("list", "transaction"), id="list"),
    pytest.param(("list", "transaction", "--allow-errors"), id="list-allow-errors"),
]
pytestmark = pytest.mark.skipif(
    sys.platform == "win32" or not hasattr(os, "geteuid") or os.geteuid() == 0,
    reason="requires POSIX permissions that bind the caller",
)


@dataclass
class Books:
    root: Path
    visible: Path
    hidden: Path
    locked: Path

    def originals(self) -> dict[Path, bytes]:
        return {p: p.read_bytes() for p in (self.root, self.visible, self.hidden)}


def _transaction(name: str, amount: int) -> str:
    return f'2026-01-02 * "{name}"\n  Assets:Cash  {amount} USD\n  Equity:Opening  {-amount} USD\n'


def _books(tmp_path: Path, *, pattern: str = "txns/**/*.bean", locked_name: str = "2025") -> Books:
    root = tmp_path / "main.bean"
    visible = tmp_path / "txns" / "2026" / "a.bean"
    locked = tmp_path / "txns" / locked_name
    visible.parent.mkdir(parents=True)
    locked.mkdir()
    hidden = locked / "b.bean"
    root.write_text(
        'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n'
        f'2026-01-01 open Equity:Opening\ninclude "{pattern}"\n'
    )
    visible.write_text(_transaction("visible", 1))
    hidden.write_text(_transaction("hidden", 2))
    return Books(root, visible, hidden, locked)


@contextmanager
def _locked(directory: Path, mode: int = 0) -> Iterator[None]:
    original = stat.S_IMODE(directory.stat().st_mode)
    directory.chmod(mode)
    try:
        assert not os.access(directory, os.R_OK)
        yield
    finally:
        directory.chmod(original)


def _run(tmp_path: Path, *args: str, as_json: bool = False) -> subprocess.CompletedProcess[str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_") and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_UPDATE_API_URL="http://127.0.0.1:9",
        BEA_TAP_FORMULA_URL="http://127.0.0.1:9/bea.rb",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
        TERM="dumb",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", *(["--json"] if as_json else []), *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _refused(done: subprocess.CompletedProcess[str], locked: Path, *, as_json: bool) -> None:
    assert done.returncode == 2, done.stdout + done.stderr
    assert done.stdout == ""
    if as_json:
        error = json.loads(done.stderr)["error"]
        assert error["category"] == "usage" and error["exit_code"] == 2
    assert str(locked) in done.stderr
    assert "Permission denied" in done.stderr
    assert "Traceback" not in done.stderr


def _balance(tmp_path: Path, books: Books) -> Decimal:
    done = _run(tmp_path, "--file", str(books.root), "balance", "Assets", as_json=True)
    assert done.returncode == 0, done.stdout + done.stderr
    return Decimal(json.loads(done.stdout)["data"]["assets"]["balance_children"]["USD"])


@pytest.mark.parametrize("args", READS)
@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_recursive_include_reads_refuse_an_unlistable_member_directory_even_with_allow_errors(
    tmp_path: Path, args: tuple[str, ...], as_json: bool
) -> None:
    books = _books(tmp_path)
    originals = books.originals()
    with _locked(books.locked):
        done = _run(tmp_path, "--file", str(books.root), *args, as_json=as_json)

        _refused(done, books.locked, as_json=as_json)
    assert books.originals() == originals


def test_a_write_cannot_commit_against_a_partial_glob_closure_even_with_allow_errors(tmp_path: Path) -> None:
    books = _books(tmp_path)
    originals = books.originals()
    with _locked(books.locked):
        done = _run(
            tmp_path,
            "--file",
            str(books.root),
            "add",
            "open",
            "--account",
            "Assets:NeverWritten",
            "--date",
            "2026-01-03",
            "--allow-errors",
            as_json=True,
        )

        _refused(done, books.locked, as_json=True)
    assert books.originals() == originals


@pytest.mark.parametrize("mode", ["--check", "--dry-run", "-i"])
@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_format_reports_the_unlistable_glob_directory_in_every_walk_mode(
    tmp_path: Path, mode: str, as_json: bool
) -> None:
    books = _books(tmp_path)
    aligned = _run(tmp_path, "format", "-i", str(books.root))
    assert aligned.returncode == 0, aligned.stdout + aligned.stderr
    originals = books.originals()
    with _locked(books.locked):
        done = _run(tmp_path, "format", mode, str(books.root), as_json=as_json)

        # Dry-run reports failures while retaining its existing status0 policy.
        assert done.returncode == 0 if mode == "--dry-run" else done.returncode != 0
        shown = done.stdout + done.stderr
        assert str(books.locked) in shown and "Permission denied" in shown
        assert "Traceback" not in shown
        if as_json:
            payload = json.loads(done.stdout if mode == "--dry-run" else done.stderr)
            data = payload["data"] if mode == "--dry-run" else payload["error"]["result"]
            assert len(data["missing"]) == 1
            assert str(books.locked) in data["missing"][0]["reason"]
    assert books.hidden.read_bytes() == originals[books.hidden]
    if mode != "-i":
        assert books.originals() == originals


@pytest.mark.parametrize("pattern_kind", ["nonrecursive", "constrained-year", "implicit-hidden"])
def test_globs_ignore_unlistable_directories_outside_their_actual_search(tmp_path: Path, pattern_kind: str) -> None:
    pattern = {"nonrecursive": "txns/*.bean", "constrained-year": "txns/2026/*.bean"}.get(
        pattern_kind, "txns/**/*.bean"
    )
    books = _books(tmp_path, pattern=pattern, locked_name=".archive" if pattern_kind == "implicit-hidden" else "2025")
    if pattern_kind == "nonrecursive":
        (tmp_path / "txns" / "top.bean").write_text(_transaction("top", 1))
    with _locked(books.locked):
        assert _balance(tmp_path, books) == Decimal(1)


@pytest.mark.parametrize("pattern_kind", ["wildcard-parent", "explicit-hidden", "symlink"])
def test_a_matched_wildcard_or_explicit_hidden_directory_must_be_listable(tmp_path: Path, pattern_kind: str) -> None:
    hidden = pattern_kind == "explicit-hidden"
    pattern = "txns/.archive/*.bean" if hidden else "txns/*/*.bean"
    books = _books(tmp_path, pattern=pattern, locked_name=".archive" if hidden else "2025")
    if pattern_kind == "symlink":
        outside = tmp_path / "outside"
        outside.mkdir()
        target = outside / "2025"
        books.locked.rename(target)
        books.locked.symlink_to(target, target_is_directory=True)
    with _locked(books.locked):
        done = _run(tmp_path, "--file", str(books.root), "balance", "Assets", as_json=True)

        _refused(done, books.locked, as_json=True)


def test_a_literal_include_can_read_a_known_file_in_an_execute_only_directory(tmp_path: Path) -> None:
    books = _books(tmp_path, pattern="txns/2025/b.bean")
    originals = books.originals()
    with _locked(books.locked, 0o111):
        assert os.access(books.hidden, os.R_OK)
        assert _balance(tmp_path, books) == Decimal(2)
    assert books.originals() == originals


def test_a_warm_load_cache_does_not_hide_permission_changes_and_restoring_access_recovers_the_full_balance(
    tmp_path: Path,
) -> None:
    books = _books(tmp_path)
    books.root.write_text('option "insert_pythonpath" "TRUE"\nplugin "slow"\n' + books.root.read_text())
    plugin = tmp_path / "slow.py"
    plugin.write_text(
        "import time\n__plugins__ = ['slow']\ndef slow(entries, options):\n"
        "    time.sleep(1.2)\n    return entries, []\n"
    )
    originals = books.originals()
    assert _balance(tmp_path, books) == Decimal(3)
    assert list((tmp_path / "cache" / "bea" / "load-cache").glob("*.picklecache")), (
        "fixture did not warm the load cache"
    )
    with _locked(books.locked):
        done = _run(tmp_path, "--file", str(books.root), "balance", "Assets", as_json=True)

        _refused(done, books.locked, as_json=True)
    assert _balance(tmp_path, books) == Decimal(3)
    assert books.originals() == originals
