"""`bea list <type> --sort` reaches every directive type (w5/161).

Only `list transaction` took `--sort`; the other ten types walked oldest first
and stopped at the limit, so a truncated `bea list price` kept the stalest
quotes and there was no way to ask for the current ones.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

START = datetime.date(2026, 1, 1)
DAYS = 60

# One directive of each type in each of two months, so either order is visible
# in a single `--limit 1` row.
EVERY_TYPE = """\
2026-01-01 commodity AAA
2026-01-01 open Assets:Cash USD
2026-01-01 open Equity:Open USD
2026-01-01 open Assets:Old USD
2026-01-02 pad Assets:Cash Equity:Open
2026-01-03 balance Assets:Cash 10 USD
2026-01-03 note Assets:Cash "first"
2026-01-03 event "location" "Paris"
2026-01-03 price AAA 1 USD
2026-01-03 document Assets:Cash "/receipts/first.pdf"
2026-01-03 custom "budget" "first"
2026-01-03 close Assets:Old
2026-02-01 commodity BBB
2026-02-01 open Assets:New USD
2026-02-02 pad Assets:Cash Equity:Open
2026-02-03 balance Assets:Cash 20 USD
2026-02-03 note Assets:Cash "second"
2026-02-03 event "location" "Rome"
2026-02-03 price AAA 2 USD
2026-02-03 document Assets:Cash "/receipts/second.pdf"
2026-02-03 custom "budget" "second"
2026-02-03 close Assets:New
"""
OTHER_TYPES = ["open", "close", "balance", "pad", "note", "event", "price", "commodity", "document", "custom"]


@pytest.fixture
def quotes(tmp_path: Path) -> Path:
    """The note's fixture: one BTC quote and one transaction a day for 60 days."""
    lines = ['option "operating_currency" "USD"', "2026-01-01 open Assets:Cash USD", "2026-01-01 open Equity:Open USD"]
    for offset in range(DAYS):
        day = START + datetime.timedelta(days=offset)
        lines.append(f"{day} price BTC {60000 + offset} USD")
        lines.append(f'{day} * "t{offset}"\n  Assets:Cash  1 USD\n  Equity:Open')
    path = tmp_path / "main.bean"
    path.write_text("\n".join(lines) + "\n")
    return path


def _rows(file: Path, *args: str) -> list[dict[str, object]]:
    result = runner.invoke(app, ["--json", "--file", str(file), "list", *args])
    assert result.exit_code == 0, result.output
    rows: list[dict[str, object]] = json.loads(result.stdout)["data"]
    return rows


def test_newest_keeps_the_current_quote_in_a_truncated_default_limit(quotes: Path) -> None:
    result = runner.invoke(app, ["--file", str(quotes), "list", "price", "--currency", "BTC", "--sort", "newest"])
    assert result.exit_code == 0, result.output
    rows = [line.split() for line in result.stdout.splitlines()[2:]]
    assert len(rows) == 50
    assert rows[0] == ["2026-03-01", "BTC", "60059", "USD"]
    assert rows[-1] == ["2026-01-11", "BTC", "60010", "USD"]

    as_json = _rows(quotes, "price", "--currency", "BTC", "--sort", "newest")
    assert [row["date"] for row in as_json] == [row[0] for row in rows]


def test_the_default_order_of_a_price_listing_is_unchanged(quotes: Path) -> None:
    default = _rows(quotes, "price", "--currency", "BTC")
    assert len(default) == 50
    assert (default[0]["date"], default[-1]["date"]) == ("2026-01-01", "2026-02-19")
    assert default == _rows(quotes, "price", "--currency", "BTC", "--sort", "oldest")


def test_transactions_still_default_to_newest_and_reverse_on_request(quotes: Path) -> None:
    assert _rows(quotes, "transaction", "--limit", "1")[0]["date"] == "2026-03-01"
    assert _rows(quotes, "transaction", "--limit", "1", "--sort", "newest")[0]["date"] == "2026-03-01"
    assert _rows(quotes, "transaction", "--limit", "1", "--sort", "oldest")[0]["date"] == "2026-01-01"


@pytest.mark.parametrize("directive", OTHER_TYPES)
def test_every_other_type_takes_sort(tmp_path: Path, directive: str) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(EVERY_TYPE)
    args = [directive, "--allow-errors", "--limit", "1"]
    oldest = _rows(ledger, *args)
    newest = _rows(ledger, *args, "--sort", "newest")
    assert str(oldest[0]["date"]).startswith("2026-01"), oldest
    assert str(newest[0]["date"]).startswith("2026-02"), newest
    assert oldest == _rows(ledger, *args, "--sort", "oldest")


def test_newest_composes_with_the_date_window(quotes: Path) -> None:
    rows = _rows(quotes, "price", "--to-date", "2026-01-31", "--limit", "2", "--sort", "newest")
    assert [row["date"] for row in rows] == ["2026-01-31", "2026-01-30"]


def test_usage_states_each_default_order() -> None:
    usage = (Path(__file__).resolve().parents[1] / "docs" / "USAGE.md").read_text()
    row = next(line for line in usage.splitlines() if line.startswith("| `--sort oldest/newest`"))
    assert "`transaction` defaults to `newest`" in row
    assert "the other ten types default to `oldest`" in row
    assert "Listings are newest\nfirst" not in usage
