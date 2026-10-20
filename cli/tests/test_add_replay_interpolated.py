"""Interpolated numbers round-trip between single and bulk add (w5/801).

A number-less `--posting` (`HOOL {100 USD}`) is answered with a null units
number, which bulk input refused with pydantic's float advice — although
USAGE promises the shapes pipe back unedited. A null units number now
interpolates at booking, as the flag spelling does. Total/per-unit `#`
costs already round-trip through the documented total-cost shape
(`{# 5 USD}` replays as `{0 # 5 USD}`, the same lot); those pins guard that.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

LEDGER = """\
2026-01-01 open Assets:Brokerage
2026-01-01 open Assets:Cash USD
"""


def _add(book: Path, *postings: str) -> Any:
    flags = [part for posting in postings for part in ("-p", posting)]
    return runner.invoke(
        app, ["--file", str(book), "--json", "add", "transaction", "t", "--date", "2026-02-01", *flags]
    )


def _replay(book: Path, directive: dict[str, Any]) -> Any:
    rows = book.parent / "rows.json"
    rows.write_text(json.dumps([directive]))
    return runner.invoke(app, ["--file", str(book), "add", "transactions", "--from", str(rows)])


def _check(book: Path) -> int:
    return int(runner.invoke(app, ["--file", str(book), "check"]).exit_code)


def _booked_cost_number(book: Path) -> str:
    listed = runner.invoke(app, ["--file", str(book), "--json", "list", "transaction"])
    assert listed.exit_code == 0, listed.output
    (txn,) = json.loads(listed.stdout)["data"]
    return str(txn["postings"][0]["cost"]["number"])


def _fresh(tmp_path: Path, name: str) -> Path:
    book = tmp_path / name
    book.write_text(LEDGER)
    return book


def test_units_less_answer_replays_to_the_same_entry(tmp_path: Path, bea_config_dir: Path) -> None:
    book = _fresh(tmp_path, "main.bean")
    added = _add(book, "Assets:Brokerage HOOL {100 USD}", "Assets:Cash -200 USD")
    assert added.exit_code == 0, added.output
    directive = json.loads(added.stdout)["data"]["directive"]
    assert directive["postings"][0]["units"] == {"number": None, "currency": "HOOL"}

    replayed = _fresh(tmp_path, "replay.bean")
    result = _replay(replayed, directive)

    assert result.exit_code == 0, result.output
    assert "Assets:Brokerage  HOOL {100 USD}" in replayed.read_text()
    assert _check(book) == 0
    assert _check(replayed) == 0
    assert _booked_cost_number(replayed) == "100"


def test_priced_units_less_answer_replays(tmp_path: Path, bea_config_dir: Path) -> None:
    book = _fresh(tmp_path, "main.bean")
    added = _add(book, "Assets:Brokerage HOOL @ 100 USD", "Assets:Cash -200 USD")
    assert added.exit_code == 0, added.output
    directive = json.loads(added.stdout)["data"]["directive"]

    replayed = _fresh(tmp_path, "replay.bean")
    result = _replay(replayed, directive)

    assert result.exit_code == 0, result.output
    assert "HOOL @ 100 USD" in replayed.read_text()
    assert _check(replayed) == 0


def test_omitted_units_number_is_a_missing_key_not_interpolation(tmp_path: Path, bea_config_dir: Path) -> None:
    book = _fresh(tmp_path, "main.bean")
    rows = tmp_path / "rows.json"
    rows.write_text(
        json.dumps(
            [
                {
                    "date": "2026-02-01",
                    "narration": "t",
                    "postings": [
                        {
                            "account": "Assets:Brokerage",
                            "units": {"currency": "HOOL"},
                            "cost": {"number": "100", "currency": "USD"},
                        },
                        {"account": "Assets:Cash", "units": {"number": "-200", "currency": "USD"}},
                    ],
                }
            ]
        )
    )

    result = runner.invoke(app, ["--file", str(book), "add", "transactions", "--from", str(rows)])

    assert result.exit_code == 1, result.output
    assert "postings.0.units.number: Field required" in " ".join(result.output.split())
    assert book.read_text() == LEDGER


def test_two_numberless_postings_are_refused_like_the_flag_path(tmp_path: Path, bea_config_dir: Path) -> None:
    book = _fresh(tmp_path, "main.bean")
    rows = tmp_path / "rows.json"
    rows.write_text(
        json.dumps(
            [
                {
                    "date": "2026-02-01",
                    "narration": "t",
                    "postings": [
                        {"account": "Assets:Brokerage", "units": {"number": None, "currency": "HOOL"}},
                        {"account": "Assets:Cash", "units": {"number": None, "currency": "USD"}},
                    ],
                }
            ]
        )
    )

    result = runner.invoke(app, ["--file", str(book), "add", "transactions", "--from", str(rows)])

    assert result.exit_code == 1, result.output
    assert "Only one posting may omit its amount" in " ".join(result.output.split())
    assert book.read_text() == LEDGER
    assert _check(book) == 0


def test_zero_inference_through_a_null_number_is_refused(tmp_path: Path, bea_config_dir: Path) -> None:
    book = _fresh(tmp_path, "main.bean")
    rows = tmp_path / "rows.json"
    rows.write_text(
        json.dumps(
            [
                {
                    "date": "2026-02-01",
                    "narration": "t",
                    "postings": [
                        {
                            "account": "Assets:Brokerage",
                            "units": {"number": None, "currency": "HOOL"},
                            "cost": {"number": "100", "currency": "USD"},
                        },
                        {"account": "Assets:Cash", "units": {"number": "0", "currency": "USD"}},
                    ],
                }
            ]
        )
    )

    result = runner.invoke(app, ["--file", str(book), "add", "transactions", "--from", str(rows)])

    assert result.exit_code == 1, result.output
    assert "zero-net transaction with an inferred balancing posting" in " ".join(result.output.split())
    assert book.read_text() == LEDGER


def test_total_cost_with_interpolated_units_fails_cleanly(tmp_path: Path, bea_config_dir: Path) -> None:
    book = _fresh(tmp_path, "main.bean")
    rows = tmp_path / "rows.json"
    rows.write_text(
        json.dumps(
            [
                {
                    "date": "2026-02-01",
                    "narration": "t",
                    "postings": [
                        {
                            "account": "Assets:Brokerage",
                            "units": {"number": None, "currency": "HOOL"},
                            "cost": {"number_total": "5", "currency": "USD"},
                        },
                        {"account": "Assets:Cash", "units": {"number": "-5", "currency": "USD"}},
                    ],
                }
            ]
        )
    )

    result = runner.invoke(app, ["--file", str(book), "add", "transactions", "--from", str(rows)])

    assert result.exit_code == 1, result.output
    # Past the schema: the row renders, and booking — not pydantic — refuses it.
    assert "Row 1: Proposed append (not written)" in " ".join(result.output.split())
    assert book.read_text() == LEDGER
    assert _check(book) == 0


def test_interpolated_buy_books_beside_a_same_day_sale(tmp_path: Path, bea_config_dir: Path) -> None:
    book = tmp_path / "main.bean"
    book.write_text(LEDGER + "2026-01-01 open Income:Gains\n")
    rows = tmp_path / "rows.json"
    rows.write_text(
        json.dumps(
            [
                {
                    "date": "2026-02-01",
                    "narration": "buy",
                    "postings": [
                        {
                            "account": "Assets:Brokerage",
                            "units": {"number": None, "currency": "HOOL"},
                            "cost": {"number": "100", "currency": "USD"},
                        },
                        {"account": "Assets:Cash", "units": {"number": "-200", "currency": "USD"}},
                    ],
                },
                {
                    "date": "2026-02-01",
                    "narration": "sell",
                    "postings": [
                        {
                            "account": "Assets:Brokerage",
                            "units": {"number": "-1", "currency": "HOOL"},
                            "cost": {"number": "100", "currency": "USD"},
                        },
                        {"account": "Assets:Cash", "units": {"number": "150", "currency": "USD"}},
                        {"account": "Income:Gains", "units": {"number": "-50", "currency": "USD"}},
                    ],
                },
            ]
        )
    )

    result = runner.invoke(app, ["--file", str(book), "add", "transactions", "--from", str(rows)])

    assert result.exit_code == 0, result.output
    assert _check(book) == 0


def test_per_unit_interpolation_replays_as_the_documented_total_cost(tmp_path: Path, bea_config_dir: Path) -> None:
    book = _fresh(tmp_path, "main.bean")
    added = _add(book, "Assets:Brokerage 2 HOOL {# 5 USD}", "Assets:Cash -5 USD")
    assert added.exit_code == 0, added.output
    directive = json.loads(added.stdout)["data"]["directive"]

    replayed = _fresh(tmp_path, "replay.bean")
    result = _replay(replayed, directive)

    assert result.exit_code == 0, result.output
    assert "{0 # 5 USD}" in replayed.read_text()
    assert _check(replayed) == 0
    assert _booked_cost_number(replayed) == _booked_cost_number(book) == "2.5"


def test_total_interpolation_replays_as_a_plain_per_unit_cost(tmp_path: Path, bea_config_dir: Path) -> None:
    book = _fresh(tmp_path, "main.bean")
    added = _add(book, "Assets:Brokerage 2 HOOL {100 # USD}", "Assets:Cash -200 USD")
    assert added.exit_code == 0, added.output
    directive = json.loads(added.stdout)["data"]["directive"]

    replayed = _fresh(tmp_path, "replay.bean")
    result = _replay(replayed, directive)

    assert result.exit_code == 0, result.output
    assert "{100 USD}" in replayed.read_text()
    assert _check(replayed) == 0
    assert _booked_cost_number(replayed) == _booked_cost_number(book) == "100"


def test_amount_shorthand_cannot_spell_a_numberless_posting(tmp_path: Path, bea_config_dir: Path) -> None:
    book = _fresh(tmp_path, "main.bean")
    rows = tmp_path / "rows.json"
    rows.write_text(
        json.dumps(
            [
                {
                    "date": "2026-02-01",
                    "narration": "t",
                    "postings": [
                        {"account": "Assets:Brokerage", "amount": "HOOL {100 USD}"},
                        {"account": "Assets:Cash", "amount": "-200 USD"},
                    ],
                }
            ]
        )
    )

    result = runner.invoke(app, ["--file", str(book), "add", "transactions", "--from", str(rows)])

    assert result.exit_code == 1, result.output
    assert "no amount found" in " ".join(result.output.split())
    assert book.read_text() == LEDGER
