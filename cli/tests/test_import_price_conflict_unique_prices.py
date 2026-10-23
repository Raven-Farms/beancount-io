"""An import price conflict does not advise a second quote the ledger forbids (w5/902).

The refusal always recommended `bea add price --force`, which `unique_prices`
turns into another conflict; `add price` already says to edit the recorded
quote.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_import_source_facts import _bea

LEDGER = (
    'option "operating_currency" "USD"\n2024-01-01 open Assets:Cash USD\n2024-01-01 open Equity:Opening USD\n'
    '2024-01-02 * "Opening"\n  Assets:Cash 100 USD\n  Equity:Opening -100 USD\n2024-02-01 price HOOL 100 USD\n'
)
IMPORTER = """from datetime import date
from decimal import Decimal
from beancount.core.data import Price, new_metadata
from beancount.core.amount import Amount

class Quotes:
    def identify(self, file): return str(file).endswith('.txt')
    def account(self, file): return 'Assets:Cash'
    def extract(self, file, existing_entries=None):
        return [Price(new_metadata(file, 1), date(2024, 2, 1), 'HOOL', Amount(Decimal('120'), 'USD'))]

CONFIG = [Quotes()]
"""
RUN = ["import", "quotes.txt", "--config", "importers.py", "--apply"]


def _books(tmp_path: Path, plugin: str) -> bytes:
    (tmp_path / "main.bean").write_text(plugin + LEDGER)
    (tmp_path / "importers.py").write_text(IMPORTER)
    (tmp_path / "quotes.txt").write_text("synthetic\n")
    return (tmp_path / "main.bean").read_bytes()


def _message(result: object) -> str:
    return " ".join(json.loads(result.stderr)["error"]["message"].split())  # type: ignore[attr-defined]


def test_the_advice_is_to_edit_the_recorded_quote(tmp_path: Path) -> None:
    before = _books(tmp_path, 'plugin "beancount.plugins.unique_prices"\n')

    result = _bea(tmp_path, *RUN)

    assert result.returncode == 4, result.stdout
    message = _message(result)
    assert "edit the recorded quote" in message and "allows one price" in message
    assert "price --force" not in message
    assert (tmp_path / "main.bean").read_bytes() == before


@pytest.mark.parametrize(
    ("plugins", "expected"),
    [
        ([], None),
        ([("beancount.plugins.unique_prices", None)], "the unique_prices plugin"),
        ([("beancount.plugins.pedantic", None)], "the pedantic plugin (which bundles unique_prices)"),
        ([("myplug", None)], None),
    ],
    ids=["none", "unique", "pedantic", "other"],
)
def test_the_policy_is_recognised_as_add_price_does(plugins: list, expected: str | None) -> None:  # type: ignore[type-arg]
    from bea_engine.ledger.adding import one_price_per_day_plugin

    assert one_price_per_day_plugin({"plugin": plugins}) == expected


def test_without_the_plugin_the_force_alternative_stays(tmp_path: Path) -> None:
    _books(tmp_path, "")

    result = _bea(tmp_path, *RUN)

    assert result.returncode == 4, result.stdout
    assert "bea add price --force" in _message(result)


def test_correcting_the_recorded_quote_lets_the_import_through_as_a_duplicate(tmp_path: Path) -> None:
    _books(tmp_path, 'plugin "beancount.plugins.unique_prices"\n')
    text = (tmp_path / "main.bean").read_text().replace("HOOL 100 USD", "HOOL 120 USD")
    (tmp_path / "main.bean").write_text(text)

    result = _bea(tmp_path, *RUN)

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["data"]["written"] == 0
