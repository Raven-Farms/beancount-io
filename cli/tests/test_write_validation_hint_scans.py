"""Write validation looks its per-error hints up instead of rescanning the ledger (w5/124).

One mis-dated `open` in a migrated ledger makes an "inactive account" error
of every transaction that uses the account. Each of those errors walked every
entry to find the account's `open`; each unbalanced conversion rebuilt the
held-at-cost set from every posting; each failing assertion re-split its
source file. A refusal `check` reports in a second took `bea add` eighteen.

Wall time is not asserted — it depends on the machine. What is asserted is
the work: passes over the ledger must not grow with the number of errors.
"""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from bea_engine import managed_load
from bea_engine.ledger import write as ledger_write
from cli.main import app

runner = CliRunner()

OPENS = """\
2000-01-01 open Assets:Bank
2000-01-01 open Assets:Broker
2000-01-01 open Expenses:Food
"""
NOTE = '2021-03-01 note Assets:Bank "hi"'


def _inactive(errors: int) -> str:
    # The note's fixture: the wallet is opened in 2030 by mistake.
    wallet = '2001-01-01 * "wallet"\n  Expenses:Food  1 USD\n  Assets:Wallet\n'
    return OPENS + "2030-01-01 open Assets:Wallet USD\n" + wallet * errors


def _conversion(errors: int) -> str:
    return OPENS + '2001-01-01 * "fx"\n  Expenses:Food  1 EUR\n  Assets:Bank  -1 USD\n' * errors


def _assertion(errors: int) -> str:
    return OPENS + "2001-01-01 balance Assets:Bank  5 USD\n" * errors


def _unknown(errors: int) -> str:
    return OPENS + '2001-01-01 * "typo"\n  Expenses:Fod  1 USD\n  Assets:Bank\n' * errors


class _CountedEntries(list[Any]):
    """The loaded entries, counting how many times something walks all of them."""

    walks = 0

    def __iter__(self) -> Any:
        type(self).walks += 1
        return super().__iter__()


class _CountedSource(bytes):
    """A ledger file's bytes, counting how many times they are split into lines."""

    splits = 0

    def splitlines(self, keepends: bool = False) -> list[bytes]:
        type(self).splits += 1
        return super().splitlines(keepends)

    def split(self, sep: Any = None, maxsplit: Any = -1) -> list[bytes]:  # type: ignore[override]
        # `lexer_lines` splits on `\n` alone, as Beancount numbers lines (w5/475).
        if sep == b"\n":
            type(self).splits += 1
        return super().split(sep, maxsplit)


def _refusal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, content: str) -> tuple[list[str], dict[str, int]]:
    """Refuse a note on `content`; return the details and the work validation did."""
    ledger = tmp_path / "main.bean"
    ledger.write_text(content)
    load_file = managed_load.load_file
    capture = ledger_write.LedgerSnapshot.capture
    close_matches = difflib.get_close_matches
    work = {"lookups": 0}

    def counted_load(*args: Any, **kwargs: Any) -> Any:
        entries, errors, options = load_file(*args, **kwargs)
        return _CountedEntries(entries), errors, options

    def counted_capture(root: Path) -> Any:
        snapshot = capture(root)
        for path, source in snapshot.contents.items():
            snapshot.contents[path] = _CountedSource(source)
        return snapshot

    def counted_matches(*args: Any, **kwargs: Any) -> list[str]:
        work["lookups"] += 1
        return close_matches(*args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(_CountedEntries, "walks", 0)
        patch.setattr(_CountedSource, "splits", 0)
        patch.setattr(managed_load, "load_file", counted_load)
        patch.setattr(ledger_write.LedgerSnapshot, "capture", counted_capture)
        patch.setattr(difflib, "get_close_matches", counted_matches)
        with pytest.raises(ledger_write.CandidateRejected) as refused:
            ledger_write.append(ledger, [NOTE])
        work.update(walks=_CountedEntries.walks, splits=_CountedSource.splits)
    assert ledger.read_text() == content
    assert len(refused.value.locations) >= content.count("2001-01-01")
    return refused.value.details, work


@pytest.mark.parametrize(
    ("fixture", "counter"),
    [(_inactive, "walks"), (_conversion, "walks"), (_assertion, "splits"), (_unknown, "lookups")],
    ids=["inactive-account", "unbalanced-conversion", "failed-assertion", "unknown-account"],
)
def test_validation_work_does_not_grow_with_the_error_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fixture: Any, counter: str
) -> None:
    (tmp_path / "few").mkdir()
    (tmp_path / "many").mkdir()
    _, few = _refusal(tmp_path / "few", monkeypatch, fixture(3))
    _, many = _refusal(tmp_path / "many", monkeypatch, fixture(60))
    assert many[counter] == few[counter], (few, many)
    # A handful of whole-file passes: since w5/475 the splits count the
    # lexer's `\n` splits as well as `splitlines`.
    assert 0 < few[counter] <= 6


def test_a_valid_ledger_pays_for_no_hint_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Control: the same books with the open dated correctly accept the note,
    # and the only pass over the entries is the one that lists open accounts.
    ledger = tmp_path / "main.bean"
    ledger.write_text(_inactive(60).replace("2030-01-01 open", "2000-01-01 open"))
    load_file = managed_load.load_file

    def counted_load(*args: Any, **kwargs: Any) -> Any:
        entries, errors, options = load_file(*args, **kwargs)
        return _CountedEntries(entries), errors, options

    monkeypatch.setattr(_CountedEntries, "walks", 0)
    monkeypatch.setattr(managed_load, "load_file", counted_load)
    assert ledger_write.append(ledger, [NOTE]) == []
    assert ledger.read_text().endswith(NOTE + "\n")
    assert _CountedEntries.walks == 1


def test_inactive_account_refusal_still_names_the_open_and_the_close(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = _inactive(3) + "2031-01-01 close Assets:Wallet\n"
    details, _ = _refusal(tmp_path, monkeypatch, content)
    ledger = tmp_path / "main.bean"
    assert details == [
        f"{ledger}:5: Invalid reference to inactive account 'Assets:Wallet' "
        f"Account opened 2030-01-01 at {ledger}:4. Account closed 2031-01-01 at {ledger}:14. "
        "Correct the transaction date or edit that directive; for new books use bea init --date YYYY-MM-DD. "
        "Same problem on 2 more lines: 8, 11."
    ]


def test_unknown_account_refusal_still_suggests_the_close_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    details, _ = _refusal(tmp_path, monkeypatch, _unknown(3))
    assert len(details) == 1
    assert (
        "unknown account 'Expenses:Fod' Did you mean Expenses:Food? "
        "To create it, use bea add open --account Expenses:Fod --date YYYY-MM-DD. "
        "Same problem on 2 more lines: 7, 10."
    ) in details[0]


def test_failed_assertion_refusal_still_points_at_each_existing_assertion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    details, _ = _refusal(tmp_path, monkeypatch, _assertion(3))
    ledger = tmp_path / "main.bean"
    for line in (4, 5, 6):
        assert any(
            detail.startswith(f"Review transactions against the existing assertion at {ledger}:{line}.")
            for detail in details
        )
    assert not any("Opening adjustment command" in detail for detail in details)


EXCHANGE = "For a currency exchange, use a price annotation"
REDUCTION = "For a commodity or stock reduction, attach a cost lot or a market price"
SALE = '2001-02-01 * "sell"\n  Assets:Broker  -1 HOOL\n  Assets:Bank  100 USD\n'


@pytest.mark.parametrize(
    ("body", "hints"),
    [
        (_conversion(2), [EXCHANGE]),
        # Held at cost by an earlier purchase: both bare sales are reductions.
        ('2001-01-01 * "buy"\n  Assets:Broker  2 HOOL {100 USD}\n  Assets:Bank\n' + SALE * 2, [REDUCTION]),
        # The only cost lot sits in the failing transaction itself, which does
        # not count as a holding for it; it does for the bare sale after it.
        (
            OPENS + '2001-01-01 * "both"\n  Assets:Broker  1 HOOL {100 USD}\n'
            "  Assets:Broker  -1 HOOL\n  Assets:Bank  7 USD\n" + SALE,
            [EXCHANGE, REDUCTION],
        ),
    ],
    ids=["conversion", "held-lot", "own-lot-only"],
)
def test_unbalanced_refusal_still_tells_a_conversion_from_a_lot_reduction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str, hints: list[str]
) -> None:
    content = body if body.startswith(OPENS) else OPENS + body
    details, _ = _refusal(tmp_path, monkeypatch, content)
    assert [hint for detail in details for hint in (EXCHANGE, REDUCTION) if detail.startswith(hint)] == hints


def test_add_refuses_the_misdated_open_with_the_same_message(tmp_path: Path) -> None:
    # The note's command, through the real frontend and engine child.
    ledger = tmp_path / "main.bean"
    ledger.write_text(_inactive(40))
    argv = ["-f", str(ledger), "add", "note", "--account", "Assets:Bank", "--comment", "hi", "--date", "2021-03-01"]
    result = runner.invoke(app, argv)
    assert result.exit_code == 1, result.output
    flat = " ".join(result.output.split())
    # The misdated open was already there; the note adds nothing wrong (w5/396).
    assert "The ledger already has 40 error(s); nothing was written. Pass --allow-errors to write anyway." in flat
    assert "Invalid reference to inactive account 'Assets:Wallet' Account opened 2030-01-01 at" in flat
    assert "Same problem on 39 more lines: 8, 11, 14," in flat
    assert ledger.read_text() == _inactive(40)

    ledger.write_text(_inactive(40).replace("2030-01-01 open", "2000-01-01 open"))
    result = runner.invoke(app, argv)
    assert result.exit_code == 0, result.output
    assert ledger.read_text().endswith('2021-03-01 note Assets:Bank "hi"\n')
