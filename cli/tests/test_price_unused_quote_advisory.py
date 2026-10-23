"""A quote no read will use says so, on every writer (w5/903).

`add price` only noticed a generated reciprocal that its simulation put ahead
of the new quote; import never looked, and a quote written into a short
included file, or forced beside an older written one, lost its day silently.
The advisory is judged on the ledger as it would load.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_import_source_facts import _bea

EUR_LEDGER = """plugin "beancount.plugins.implicit_prices"
option "operating_currency" "USD"
2024-01-01 open Assets:EUR EUR
2024-01-01 open Assets:USD USD
2024-01-01 open Equity:Opening
2024-01-02 * "Opening"
  Assets:EUR 1000 EUR
  Equity:Opening -1000 EUR
2024-01-05 * "Exchange"
  Assets:USD 100 USD @ 0.80 EUR
  Assets:EUR -80 EUR
"""
IMPORTER = """from datetime import date
from decimal import Decimal
from beancount.core.data import Price, new_metadata
from beancount.core.amount import Amount

class Quotes:
    def identify(self, file): return str(file).endswith('.txt')
    def account(self, file): return 'Assets:EUR'
    def extract(self, file, existing_entries=None):
        return [Price(new_metadata(file, 1), date(2024, 1, 5), 'EUR', Amount(Decimal('1.20'), 'USD'))]

CONFIG = [Quotes()]
"""


def _warnings(result: object) -> list[str]:
    assert result.returncode == 0, result.stderr  # type: ignore[attr-defined]
    data = json.loads(result.stdout)["data"]  # type: ignore[attr-defined]
    return list(data.get("warnings") if "warnings" in data else data["validation_warnings"])


def _import(tmp_path: Path, ledger: str, *flags: str) -> object:
    (tmp_path / "main.bean").write_text(ledger)
    (tmp_path / "importers.py").write_text(IMPORTER)
    (tmp_path / "quotes.txt").write_text("synthetic\n")
    return _bea(tmp_path, "import", "quotes.txt", "--config", "importers.py", *flags)


@pytest.mark.parametrize("flags", [[], ["--apply"]], ids=["preview", "apply"])
def test_import_explains_a_quote_a_generated_reciprocal_beats(tmp_path: Path, flags: list[str]) -> None:
    warnings = _warnings(_import(tmp_path, EUR_LEDGER, *flags))

    assert len(warnings) == 1
    assert "USD already has a 2024-01-05 price of 0.80 EUR implied at" in warnings[0]
    assert "the new quote is never used" in warnings[0]


def test_import_is_quiet_when_the_quote_is_effective(tmp_path: Path) -> None:
    assert _warnings(_import(tmp_path, EUR_LEDGER.replace("plugin", "; plugin", 1), "--apply")) == []


def test_add_price_into_a_short_included_file_warns(tmp_path: Path) -> None:
    (tmp_path / "prices.bean").write_text("; quote file\n")
    (tmp_path / "main.bean").write_text(
        'include "prices.bean"\n'
        + EUR_LEDGER.replace("Assets:USD 100 USD @ 0.80 EUR", "Assets:EUR 100 EUR @ 1.25 USD").replace(
            "Assets:EUR -80 EUR", "Assets:USD -125 USD"
        )
    )

    result = _bea(
        tmp_path, "add", "price", "--date", "2024-01-05", "--currency", "EUR", "--amount", "1.20 USD",
        "--into", "prices.bean",
    )  # fmt: skip

    (warning,) = _warnings(result)
    assert "EUR already has a 2024-01-05 price of 1.25 USD implied at" in warning


def test_a_forced_correction_that_loses_to_an_older_written_quote_warns(tmp_path: Path) -> None:
    (tmp_path / "prices.bean").write_text("; old quote\n" * 39 + "2024-01-03 price HOOL 20 USD\n")
    (tmp_path / "corrections.bean").write_text("; corrections\n")
    (tmp_path / "main.bean").write_text(
        'option "operating_currency" "USD"\n2024-01-01 open Assets:Cash USD\n2024-01-01 open Assets:Stock HOOL\n'
        '2024-01-01 open Equity:Opening USD\n2024-01-01 * "Capital"\n  Assets:Cash 100 USD\n'
        '  Equity:Opening -100 USD\n2024-01-02 * "Buy"\n  Assets:Stock 1 HOOL {10 USD}\n  Assets:Cash -10 USD\n'
        'include "prices.bean"\ninclude "corrections.bean"\n'
    )

    result = _bea(
        tmp_path, "add", "price", "--date", "2024-01-03", "--currency", "HOOL", "--amount", "22 USD", "--force",
        "--into", "corrections.bean",
    )  # fmt: skip

    (warning,) = _warnings(result)
    assert "HOOL already has a 2024-01-03 price of 20 USD at" in warning and "prices.bean:40" in warning
    assert "implied" not in warning


def test_an_effective_forced_quote_stays_quiet(tmp_path: Path) -> None:
    (tmp_path / "prices.bean").write_text("2024-01-03 price HOOL 20 USD\n")
    (tmp_path / "main.bean").write_text(
        'option "operating_currency" "USD"\n2024-01-01 open Assets:Stock HOOL\ninclude "prices.bean"\n'
    )

    result = _bea(
        tmp_path, "add", "price", "--date", "2024-01-03", "--currency", "HOOL", "--amount", "22 USD", "--force",
        "--into", "prices.bean",
    )  # fmt: skip

    assert _warnings(result) == []
