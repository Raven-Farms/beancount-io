"""Posting-grammar slips refuse or render honestly (w5/805).

`{{240}}` failed as "a value that is not one token", an empty lot label was
dropped so lots merged, and bulk shorthand refusals misdescribed valid
input.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

LEDGER = """\
option "operating_currency" "USD"
2026-01-01 open Assets:Brokerage
2026-01-01 open Assets:Cash USD
"""

LOTTED = (
    LEDGER
    + """\
2026-01-15 * "Buy"
  Assets:Brokerage  1 HOOL {100 USD}
  Assets:Cash -100 USD
"""
)


def _add(book: Path, *postings: str) -> Any:
    flags = [part for posting in postings for part in ("-p", posting)]
    return runner.invoke(
        app, ["--file", str(book), "--json", "add", "transaction", "t", "--date", "2026-02-01", *flags]
    )


def _bulk(book: Path, rows: list[dict[str, Any]]) -> Any:
    source = book.parent / "rows.json"
    source.write_text(json.dumps(rows))
    return runner.invoke(app, ["--file", str(book), "add", "transactions", "--from", str(source)])


def _flat(result: Any) -> str:
    return " ".join(result.output.split())


def test_currency_less_total_cost_names_the_missing_currency(tmp_path: Path, bea_config_dir: Path) -> None:
    book = tmp_path / "main.bean"
    book.write_text(LEDGER)

    result = _add(book, "Assets:Brokerage 3 HOOL {{240}}", "Assets:Cash -240 USD")

    assert result.exit_code == 2, result.output
    flat = _flat(result)
    assert "--posting 1" in flat
    assert "total cost 240 has no currency; a total cost needs one" in flat
    assert "not one token" not in flat
    assert book.read_text() == LEDGER


def test_currency_ful_and_per_unit_costs_still_write(tmp_path: Path, bea_config_dir: Path) -> None:
    for leg, cash in [
        ("Assets:Brokerage 3 HOOL {{240 USD}}", "Assets:Cash -240 USD"),
        ("Assets:Brokerage 3 HOOL {# 240 USD}", "Assets:Cash -240 USD"),
        ("Assets:Brokerage 3 HOOL {80}", "Assets:Cash -240 USD"),
        ("Assets:Brokerage 3 HOOL {100 # USD}", "Assets:Cash -300 USD"),
    ]:
        book = tmp_path / "main.bean"
        book.write_text(LEDGER)

        result = _add(book, leg, cash)

        assert result.exit_code == 0, (leg, result.output)
        assert runner.invoke(app, ["--file", str(book), "check"]).exit_code == 0


def test_empty_lot_label_is_written_and_stays_a_distinct_lot(tmp_path: Path, bea_config_dir: Path) -> None:
    book = tmp_path / "main.bean"
    book.write_text(LOTTED)

    result = _add(book, 'Assets:Brokerage 1 HOOL {100 USD, ""}', "Assets:Cash -100 USD")

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["data"]["directive"]["postings"][0]["cost"]["label"] == ""
    assert '1 HOOL {100 USD, ""}' in book.read_text()
    assert runner.invoke(app, ["--file", str(book), "check"]).exit_code == 0


def test_bulk_structured_empty_label_is_written(tmp_path: Path, bea_config_dir: Path) -> None:
    book = tmp_path / "main.bean"
    book.write_text(LEDGER)

    result = _bulk(
        book,
        [
            {
                "date": "2026-02-01",
                "narration": "t",
                "postings": [
                    {
                        "account": "Assets:Brokerage",
                        "units": {"number": "1", "currency": "HOOL"},
                        "cost": {"number": "100", "currency": "USD", "label": ""},
                    },
                    {"account": "Assets:Cash", "units": {"number": "-100", "currency": "USD"}},
                ],
            }
        ],
    )

    assert result.exit_code == 0, result.output
    assert '1 HOOL {100 USD, ""}' in book.read_text()


def test_currency_less_shorthand_says_no_currency(tmp_path: Path, bea_config_dir: Path) -> None:
    book = tmp_path / "main.bean"
    book.write_text(LEDGER)

    result = _bulk(
        book,
        [
            {
                "date": "2026-02-01",
                "narration": "t",
                "postings": [
                    {"account": "Assets:Brokerage", "amount": "10"},
                    {"account": "Assets:Cash"},
                ],
            }
        ],
    )

    assert result.exit_code == 1, result.output
    assert "no currency found" in _flat(result)
    assert book.read_text() == LEDGER


def test_compound_cost_shorthand_points_to_structured_cost(tmp_path: Path, bea_config_dir: Path) -> None:
    book = tmp_path / "main.bean"
    book.write_text(LEDGER)

    result = _bulk(
        book,
        [
            {
                "date": "2026-02-01",
                "narration": "t",
                "postings": [
                    {"account": "Assets:Brokerage", "amount": "2 HOOL {100 # 5 USD}"},
                    {"account": "Assets:Cash"},
                ],
            }
        ],
    )

    assert result.exit_code == 1, result.output
    flat = _flat(result)
    assert "uses a per-unit cost with a total" in flat
    assert 'structured "cost" carrying "number", "number_total" and "currency"' in flat
    assert "total cost '{{...}}'" not in flat
    assert book.read_text() == LEDGER


def test_pure_total_shorthand_keeps_both_remedies(tmp_path: Path, bea_config_dir: Path) -> None:
    # A pure total (`{{...}}`, `{# ...}`) is accurately described as a total
    # cost; w3/240 pins the split-or-structured remedies, so only genuinely
    # compound costs get the new telling.
    for amount in ["2 HOOL {# 5 USD}", "2 HOOL {{5 USD}}"]:
        book = tmp_path / "main.bean"
        book.write_text(LEDGER)

        result = _bulk(
            book,
            [
                {
                    "date": "2026-02-01",
                    "narration": "t",
                    "postings": [{"account": "Assets:Brokerage", "amount": amount}, {"account": "Assets:Cash"}],
                }
            ],
        )

        assert result.exit_code == 1, (amount, result.output)
        flat = _flat(result)
        assert "uses a total cost '{{...}}'" in flat
        assert "Split the lot into a per-unit cost" in flat
        assert 'structured "cost" carrying "number_total" and "currency"' in flat
        assert "per-unit cost with a total" not in flat
        assert book.read_text() == LEDGER


def test_structured_compound_cost_writes(tmp_path: Path, bea_config_dir: Path) -> None:
    book = tmp_path / "main.bean"
    book.write_text(LEDGER)

    result = _bulk(
        book,
        [
            {
                "date": "2026-02-01",
                "narration": "t",
                "postings": [
                    {
                        "account": "Assets:Brokerage",
                        "units": {"number": "2", "currency": "HOOL"},
                        "cost": {"number": "100", "number_total": "200", "currency": "USD"},
                    },
                    {"account": "Assets:Cash", "units": {"number": "-400", "currency": "USD"}},
                ],
            }
        ],
    )

    # Upstream weighs per-unit and total together: 2 x 100 + 200 against -400.
    assert result.exit_code == 0, result.output
    assert "{100 # 200 USD}" in book.read_text()
    assert runner.invoke(app, ["--file", str(book), "check"]).exit_code == 0
