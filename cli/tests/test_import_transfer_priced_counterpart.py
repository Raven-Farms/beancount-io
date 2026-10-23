"""A transfer's second side matches a booked posting that carries a price or cost (w5/931).

The counterpart index keyed amounts by currency *and* price, and the legs
comparison needed an incoming cost to agree, so the receiving bank's plain
`100.00 EUR` never met the booked `100.00 EUR @ 1.10 USD`: preview said `new`,
`--duplicates skip` wrote it, and one conversion doubled the euros.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_import_source_facts import _bea

HEADER = """option "operating_currency" "USD"
2024-01-01 open Assets:Dollars USD
2024-01-01 open Assets:Euros EUR
2024-01-01 open Expenses:Uncategorized EUR
2024-01-01 open Equity:Capital USD
2024-01-02 * "Capital"
  Assets:Dollars 1000.00 USD
  Equity:Capital -1000.00 USD
2024-02-01 price EUR 1.10 USD
"""
BOOKED = """2024-02-01 * "USD wire conversion"
  bank_id: "usd-fx-1"
  import-id: "bank:usd-fx-1"
  Assets:Dollars -110.00 USD
  Assets:Euros {receiving}
"""
CSV = "Date,Description,Amount,Reference\n2024-02-01,Incoming EUR transfer,{amount},eur-fx-1\n"
MAPPING = "date=Date,narration=Description,amount=Amount,id=Reference"


def _run(tmp_path: Path, receiving: str, amount: str = "100.00", *flags: str) -> tuple[int, dict[str, object]]:
    (tmp_path / "main.bean").write_text(HEADER + BOOKED.format(receiving=receiving))
    (tmp_path / "eur.csv").write_text(CSV.format(amount=amount))
    result = _bea(
        tmp_path,
        "import",
        "eur.csv",
        "--csv",
        MAPPING,
        "--account",
        "Assets:Euros",
        "--default-account",
        "Expenses:Uncategorized",
        *flags,
    )
    return result.returncode, json.loads(result.stdout or result.stderr)


def _rows(payload: dict[str, object]) -> list[dict[str, object]]:
    data = payload["data"] if "data" in payload else payload["error"]["result"]  # type: ignore[index]
    return list(data["rows"])  # type: ignore[index]


@pytest.mark.parametrize("receiving", ["100.00 EUR @ 1.10 USD", "100.00 EUR {1.10 USD}"])
def test_the_receiving_row_is_a_possible_duplicate(tmp_path: Path, receiving: str) -> None:
    code, payload = _run(tmp_path, receiving)

    assert code == 0, payload
    assert [row["status"] for row in _rows(payload)] == ["possible_duplicate"]


@pytest.mark.parametrize("receiving", ["100.00 EUR @ 1.10 USD", "100.00 EUR {1.10 USD}"])
def test_skip_writes_nothing_and_keeps_the_cash(tmp_path: Path, receiving: str) -> None:
    code, _ = _run(tmp_path, receiving, "100.00", "--duplicates", "skip", "--apply")
    before = (tmp_path / "main.bean").read_text()

    assert code == 0
    assert before.count("Incoming EUR transfer") == 0
    result = _bea(tmp_path, "query", "SELECT sum(number) WHERE account = 'Assets:Euros'")
    assert json.loads(result.stdout)["data"]["rows"] == [["100.00"]]


def test_a_different_amount_is_still_new(tmp_path: Path) -> None:
    code, payload = _run(tmp_path, "100.00 EUR @ 1.10 USD", "90.00")

    assert code == 0, payload
    assert [row["status"] for row in _rows(payload)] == ["new"]
