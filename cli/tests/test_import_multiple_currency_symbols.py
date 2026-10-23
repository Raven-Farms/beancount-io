"""Every recognized currency symbol in an amount cell must agree (w5/927).

The guard returned at the first recognized symbol, so `-£4.50€` on a GBP
account was booked as −4.50 GBP while the reversed `-€4.50£` was refused.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.test_import_source_facts import _bea, _written

BASE = ["import", "bank.csv", "--account", "Assets:Cash", "--default-account", "Expenses:Food"]
MAPPING = "date=Date,narration=Description,amount=Amount,id=Reference"


def _books(tmp_path: Path, currency: str, cell: str) -> None:
    (tmp_path / "main.bean").write_text(
        f'option "operating_currency" "{currency}"\n2024-01-01 open Assets:Cash {currency}\n'
        f"2024-01-01 open Expenses:Food {currency}\n"
    )
    (tmp_path / "bank.csv").write_text(
        f"Date,Description,Amount,Reference\n2024-02-01,Coffee,{cell},coffee-1\n", encoding="utf-8"
    )


@pytest.mark.parametrize(
    ("currency", "cell"),
    [("GBP", "-£4.50€"), ("EUR", "-€4.50£"), ("RUB", "-₽4.50€"), ("GBP", "-€4.50£")],
    ids=["gbp-then-eur", "eur-then-gbp", "rub-then-eur", "eur-first-on-gbp"],
)
def test_a_cell_with_a_contradicting_second_symbol_is_refused(tmp_path: Path, currency: str, cell: str) -> None:
    _books(tmp_path, currency, cell)
    before = (tmp_path / "main.bean").read_bytes()

    for flags in ([], ["--apply"]):
        refused = _bea(tmp_path, *BASE, "--csv", MAPPING, *flags)

        assert refused.returncode == 2, refused.stdout
        assert (tmp_path / "main.bean").read_bytes() == before


@pytest.mark.parametrize(
    ("currency", "cell"),
    [("GBP", "-£4.50£"), ("EUR", "-€4.50€"), ("EUR", "-$4.50€"), ("GBP", "-£4.50")],
    ids=["repeated-gbp", "repeated-eur", "ambiguous-dollar", "single"],
)
def test_compatible_symbols_still_import(tmp_path: Path, currency: str, cell: str) -> None:
    _books(tmp_path, currency, cell)

    assert _written(_bea(tmp_path, *BASE, "--csv", MAPPING, "--apply")) == 1
    assert f"-4.50 {currency}" in (tmp_path / "main.bean").read_text()
