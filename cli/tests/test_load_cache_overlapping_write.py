"""A load that overlaps a write must not leave a load cache behind (w5/218).

Beancount parses the ledger's files first and fingerprints them — size and
mtime — only once the load is done, then caches a load that took a second. A
`bea add` committing in between was cached as the old entries under the new
fingerprint, and every later read trusted it: the exit-0 transaction was in
the file but missing from `query` and `list`, and `import --apply` of the same
transaction found no duplicate and wrote it again.

The cache threshold is dropped to zero so a tiny fixture caches the way a
large ledger does, and the write is made to land exactly where the race puts
it: after the parse, as the loader computes its fingerprint.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bea_engine import managed_load
from bea_engine.ledger.write import pickle_cache_of
from cli.main import app

runner = CliRunner()

OPENS = "2020-01-01 open Assets:Cash USD\n2020-01-01 open Expenses:Food USD\n"
OLD = '2021-01-01 * "old"\n  Expenses:Food  1.00 USD\n  Assets:Cash\n'
LUNCH = '\n2022-02-01 * "Lunch"\n  Expenses:Food  100.00 USD\n  Assets:Cash\n'
CSV = "Date,Description,Amount\n2022-02-01,Lunch,-100.00\n"


@pytest.fixture(autouse=True)
def _always_cache(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
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


def _during_the_next_load(monkeypatch: pytest.MonkeyPatch, write: Callable[[], None]) -> None:
    """Run `write` once, between the next load's parse and its fingerprint."""
    from beancount import loader

    fingerprint = loader.compute_input_hash
    pending = [write]

    def overlapped(filenames: object) -> object:
        while pending:
            pending.pop()()
        return fingerprint(filenames)

    monkeypatch.setattr(loader, "compute_input_hash", overlapped)


def _narrations(root: Path) -> list[str]:
    entries, _errors, _options = managed_load.load_file(root)
    return sorted(getattr(entry, "narration", "") for entry in entries if hasattr(entry, "narration"))


def _bea(root: Path, *args: str) -> tuple[int, str]:
    result = runner.invoke(app, ["--json", "--file", str(root), *args])
    return result.exit_code, result.output


def _add_lunch(root: Path) -> None:
    code, output = _bea(
        root,
        "add",
        "transaction",
        "Lunch",
        "--date",
        "2022-02-01",
        "-p",
        "Expenses:Food 100.00 USD",
        "-p",
        "Assets:Cash",
    )
    assert code == 0, output


def _ledger(tmp_path: Path) -> Path:
    root = tmp_path / "main.bean"
    root.write_text(OPENS + OLD, encoding="utf-8")
    (tmp_path / "x.csv").write_text(CSV, encoding="utf-8")
    return root


def _later_reads(root: Path) -> tuple[str, int, int, int]:
    """What the commands after the race answer: the cash total, the Lunch rows, the import's exit, the file."""
    _code, total = _bea(root, "query", "SELECT sum(position) WHERE account='Assets:Cash'")
    code, listed = _bea(root, "list", "transaction", "--search", "Lunch")
    assert code == 0, listed
    imported, _output = _bea(
        root,
        "import",
        str(root.with_name("x.csv")),
        "--csv",
        "date=Date,amount=Amount,narration=Description",
        "--account",
        "Assets:Cash",
        "--default-account",
        "Expenses:Food",
        "--apply",
    )
    return total, listed.count('"Lunch"'), imported, root.read_text(encoding="utf-8").count('"Lunch"')


def test_an_add_committing_during_a_read_is_seen_by_every_later_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _ledger(tmp_path)
    _during_the_next_load(monkeypatch, lambda: _add_lunch(root))

    managed_load.load_file(root)  # the read the add overlapped; either answer is its to give

    assert '"Lunch"' in root.read_text(encoding="utf-8"), "the add must have committed during the load"
    cached = pickle_cache_of(root).exists()
    total, listed, imported, in_file = _later_reads(root)
    assert "-101.00" in total, total
    assert listed == 1
    # Exit 4: the ledger already holds this transaction, so the import needs review.
    assert imported == 4
    assert in_file == 1
    assert not cached, "a load that overlapped a write must not be cached"


def test_the_same_commands_one_after_another_are_the_control(tmp_path: Path) -> None:
    root = _ledger(tmp_path)

    _add_lunch(root)
    managed_load.load_file(root)

    assert pickle_cache_of(root).exists(), "a load nothing overlapped is still cached"
    total, listed, imported, in_file = _later_reads(root)
    assert "-101.00" in total, total
    assert (listed, imported, in_file) == (1, 4, 1)


@pytest.mark.parametrize("edited", ["main.bean", "txns/jan.bean"])
def test_a_hand_edit_during_a_load_is_read_by_the_next_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, edited: str
) -> None:
    """The same window without `bea add`, in the root and in an included file, edited in place."""
    root = tmp_path / "main.bean"
    root.write_text(OPENS + 'include "txns/*.bean"\n', encoding="utf-8")
    (tmp_path / "txns").mkdir()
    (tmp_path / "txns" / "jan.bean").write_text(OLD, encoding="utf-8")

    def edit() -> None:
        with (tmp_path / edited).open("a", encoding="utf-8") as stream:
            stream.write(LUNCH)

    _during_the_next_load(monkeypatch, edit)

    assert _narrations(root) == ["old"]
    cached = pickle_cache_of(root).exists()
    assert _narrations(root) == ["Lunch", "old"]
    assert not cached, "a load that overlapped a change must not be cached"
    assert pickle_cache_of(root).exists(), "the load after the change is cached again"


def test_a_stale_cache_refreshed_by_an_overlapped_load_is_dropped_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A warm cache does not narrow the window: the reload it triggers is the same unguarded load."""
    root = _ledger(tmp_path)
    assert _narrations(root) == ["old"]
    assert pickle_cache_of(root).exists(), "the warm cache is the precondition"
    root.write_text(OPENS + OLD + LUNCH.replace("Lunch", "Breakfast"), encoding="utf-8")

    from beancount import loader

    fingerprint = loader.compute_input_hash
    calls: list[object] = []

    def overlapped(filenames: object) -> object:
        calls.append(filenames)
        if len(calls) == 2:  # the first call judges the warm cache; the second fingerprints the reload
            with root.open("a", encoding="utf-8") as stream:
                stream.write(LUNCH)
        return fingerprint(filenames)

    monkeypatch.setattr(loader, "compute_input_hash", overlapped)

    assert _narrations(root) == ["Breakfast", "old"]
    assert _narrations(root) == ["Breakfast", "Lunch", "old"]


def test_an_unchanged_ledger_still_reads_from_the_cache(tmp_path: Path) -> None:
    """The control: large ledgers depend on the cache, so a clean hit must stay a hit."""
    root = _ledger(tmp_path)
    assert _narrations(root) == ["old"]
    cache = pickle_cache_of(root)
    aged = cache.stat().st_mtime_ns - 10**9
    os.utime(cache, ns=(aged, aged))

    assert _narrations(root) == ["old"]
    assert _narrations(root) == ["old"]
    assert cache.stat().st_mtime_ns == aged, "a hit must not rewrite or drop the cache"
    code, listed = _bea(root, "list", "transaction")
    assert code == 0, listed
    assert [item["narration"] for item in json.loads(listed)["data"]] == ["old"]
    assert cache.stat().st_mtime_ns == aged
