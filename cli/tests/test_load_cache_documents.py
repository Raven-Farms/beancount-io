"""The load cache must not freeze whether a `document` file exists (w5/116).

Beancount keys its pickle cache on the ledger files a load read, while the
load also judges whether each attachment exists and lists what a `documents`
root holds. On a ledger slow enough to be cached, removing an attachment left
`bea check` exiting 0 while every write was refused for the error `check`
denied, `--allow-errors` included; restoring one left `check` failing until
a ledger file was touched.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from bea_engine import managed_load
from cli.main import app

runner = CliRunner()

# Beancount caches a load only when it took a second; this plugin makes a
# small ledger that slow without sixty thousand transactions.
SLOW_PLUGIN = """\
import time

__plugins__ = ["slow"]


def slow(entries, options_map):
    time.sleep(1.05)
    return entries, []
"""
HEADER = 'option "insert_pythonpath" "TRUE"\nplugin "w5_116_slow"\n2000-01-01 open Assets:Bank USD\n'
DOCUMENT = '2021-03-01 document Assets:Bank "receipts/stmt.pdf"\n'
MISSING = "File does not exist"


def _ledger(tmp_path: Path, text: str, *, attachment: bool) -> Path:
    (tmp_path / "w5_116_slow.py").write_text(SLOW_PLUGIN)
    (tmp_path / "receipts").mkdir()
    if attachment:
        (tmp_path / "receipts" / "stmt.pdf").write_text("statement")
    ledger = tmp_path / "main.bean"
    ledger.write_text(text)
    return ledger


def _bea(ledger: Path, *args: str, as_json: bool = False) -> Any:
    return runner.invoke(app, [*(["--json"] if as_json else []), "--file", str(ledger), *args])


def _cache(ledger: Path) -> Path:
    return ledger.with_name(f".{ledger.name}.picklecache")


def test_removing_an_attachment_fails_check_and_keeps_allow_errors_working(
    tmp_path: Path, bea_config_dir: Path
) -> None:
    ledger = _ledger(tmp_path, HEADER + DOCUMENT, attachment=True)

    assert _bea(ledger, "check").exit_code == 0
    assert _cache(ledger).exists(), "the fixture must be slow enough to be cached"

    (tmp_path / "receipts" / "stmt.pdf").unlink()

    plain = _bea(ledger, "check")
    assert plain.exit_code == 1, plain.output
    assert MISSING in plain.output
    checked = _bea(ledger, "check", as_json=True)
    assert checked.exit_code == 1, checked.output
    assert MISSING in checked.output
    # The missing attachment is already in the books, so it is not "new".
    added = _bea(
        ledger, "add", "note", "--account", "Assets:Bank", "--comment", "hi", "--date", "2021-04-01", "--allow-errors"
    )
    assert added.exit_code == 0, added.output
    assert '2021-04-01 note Assets:Bank "hi"' in ledger.read_text()


def test_restoring_an_attachment_passes_check_without_touching_the_ledger(tmp_path: Path, bea_config_dir: Path) -> None:
    ledger = _ledger(tmp_path, HEADER + DOCUMENT, attachment=False)

    failed = _bea(ledger, "check", as_json=True)
    assert failed.exit_code == 1, failed.output
    assert MISSING in failed.output
    assert _cache(ledger).exists(), "the fixture must be slow enough to be cached"
    written = ledger.stat().st_mtime_ns

    (tmp_path / "receipts" / "stmt.pdf").write_text("statement")

    assert _bea(ledger, "check").exit_code == 0
    checked = _bea(ledger, "check", as_json=True)
    assert checked.exit_code == 0, checked.output
    assert json.loads(checked.output)["data"] == {"valid": True, "errors": []}
    assert ledger.stat().st_mtime_ns == written


@pytest.mark.parametrize("text", [HEADER, HEADER + DOCUMENT], ids=["no-documents", "attachment-unchanged"])
def test_an_unchanged_ledger_still_reads_from_the_cache(tmp_path: Path, bea_config_dir: Path, text: str) -> None:
    """The control: large ledgers depend on the cache, so a clean hit must stay a hit."""
    ledger = _ledger(tmp_path, text, attachment=True)

    assert _bea(ledger, "check").exit_code == 0
    assert _cache(ledger).exists()
    written = _cache(ledger).stat().st_mtime_ns

    assert _bea(ledger, "check").exit_code == 0
    assert _bea(ledger, "check", as_json=True).exit_code == 0
    assert _cache(ledger).stat().st_mtime_ns == written


@pytest.fixture
def always_cache(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Drop the cache threshold so an in-process load of a tiny ledger is cached."""
    from beancount import loader

    monkeypatch.delenv("BEANCOUNT_DISABLE_LOAD_CACHE", raising=False)
    monkeypatch.delenv("BEANCOUNT_LOAD_CACHE_FILENAME", raising=False)
    # `initialize` binds the threshold when it builds the cached loader, so the
    # constant alone would leave the test proving nothing.
    monkeypatch.setattr(loader, "PICKLE_CACHE_THRESHOLD", 0.0)
    loader.initialize(use_cache=True)
    try:
        yield
    finally:
        monkeypatch.undo()
        loader.initialize(os.getenv("BEANCOUNT_DISABLE_LOAD_CACHE") is None)


def _documents(root: Path) -> tuple[list[str], list[str]]:
    from beancount.core.data import Document

    entries, errors, _options = managed_load.load_file(root)
    names = sorted(Path(entry.filename).name for entry in entries if isinstance(entry, Document))
    return names, [error.message for error in errors]


def test_a_documents_root_is_listed_again_when_its_files_change(tmp_path: Path, always_cache: None) -> None:
    root = tmp_path / "main.bean"
    root.write_text('option "documents" "docs"\n2000-01-01 open Assets:Bank USD\n', encoding="utf-8")

    names, errors = _documents(root)
    assert names == []
    assert any("does not exist" in message for message in errors)
    assert _cache(root).exists(), "the warm cache is the precondition"

    folder = tmp_path / "docs" / "Assets" / "Bank"
    folder.mkdir(parents=True)
    assert _documents(root) == ([], [])

    (folder / "2021-03-01.stmt.pdf").write_text("statement")
    assert _documents(root) == (["2021-03-01.stmt.pdf"], [])

    aged = _cache(root).stat().st_mtime_ns - 10**9
    os.utime(_cache(root), ns=(aged, aged))
    assert _documents(root) == (["2021-03-01.stmt.pdf"], [])
    assert _cache(root).stat().st_mtime_ns == aged, "a hit must not rewrite the cache"

    (folder / "2021-03-01.stmt.pdf").unlink()
    assert _documents(root) == ([], [])
