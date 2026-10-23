"""The missing-price route explanation covers the lots the report actually shows (w5/905).

It borrowed the cost currency of any account's lot, so a filtered EUR-cost
holding was told a USD route would value it, and in a mixed account the route
read as if it settled the whole price gap.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_import_source_facts import _bea

PRICES = "2024-03-10 price HOOL 120 USD\n2024-03-10 price USD 0.90 EUR\n"
SPLIT = (
    'option "operating_currency" "EUR"\n2024-01-01 open Assets:Cash USD,EUR\n'
    "2024-01-01 open Assets:HoldUSD HOOL\n2024-01-01 open Assets:HoldEUR HOOL\n"
    '2024-01-02 * "USD-cost lot"\n  Assets:HoldUSD 10 HOOL {100 USD}\n  Assets:Cash -1000 USD\n'
    '2024-01-03 * "EUR-cost lot"\n  Assets:HoldEUR 10 HOOL {90 EUR}\n  Assets:Cash -900 EUR\n' + PRICES
)
MIXED = (
    'option "operating_currency" "EUR"\n2024-01-01 open Assets:Cash USD,EUR\n2024-01-01 open Assets:Hold HOOL\n'
    '2024-01-02 * "USD-cost lot"\n  Assets:Hold 10 HOOL {100 USD}\n  Assets:Cash -1000 USD\n'
    '2024-01-03 * "EUR-cost lot"\n  Assets:Hold 10 HOOL {90 EUR}\n  Assets:Cash -900 EUR\n' + PRICES
)
DATED = "HOOL → EUR has no price before 2024-03-10; earlier rows shown in HOOL"
UNDATED = "HOOL has no EUR price at any date; shown in units"


def _summary(tmp_path: Path, ledger: str, *args: str) -> list[str]:
    (tmp_path / "main.bean").write_text(ledger)
    result = _bea(tmp_path, *args, "--conversion", "EUR", "--allow-errors")
    assert result.returncode == 0, result.stderr
    return list(json.loads(result.stdout)["data"]["missing_price_summary"])


def _balance(account: str, month: str) -> tuple[str, ...]:
    return ("balance", account, "--time", month)


def _sheet(account: str, month: str) -> tuple[str, ...]:
    return ("report", "balance-sheet", "--account", account, "--time", month)


@pytest.mark.parametrize("command", [_balance, _sheet], ids=["balance", "balance-sheet"])
def test_a_selected_eur_cost_account_is_not_told_about_another_accounts_usd_route(
    tmp_path: Path, command: object
) -> None:
    assert _summary(tmp_path, SPLIT, *command("Assets:HoldEUR", "2024-02")) == [UNDATED]  # type: ignore[operator]
    assert _summary(tmp_path, SPLIT, *command("Assets:HoldEUR", "2024-04")) == [UNDATED]  # type: ignore[operator]


@pytest.mark.parametrize("command", [_balance, _sheet], ids=["balance", "balance-sheet"])
def test_a_selected_usd_cost_account_keeps_its_dated_route(tmp_path: Path, command: object) -> None:
    assert _summary(tmp_path, SPLIT, *command("Assets:HoldUSD", "2024-02")) == [DATED]  # type: ignore[operator]


def test_a_direct_quote_keeps_the_dated_wording_for_the_eur_cost_account(tmp_path: Path) -> None:
    ledger = SPLIT + "2024-03-10 price HOOL 110 EUR\n"

    assert _summary(tmp_path, ledger, *_balance("Assets:HoldEUR", "2024-02")) == [DATED]


@pytest.mark.parametrize("lot", ["10 HOOL {90 EUR}", "10 HOOL @ 90 EUR"], ids=["eur-cost", "costless"])
@pytest.mark.parametrize("command", [_balance, _sheet], ids=["balance", "balance-sheet"])
def test_a_mixed_account_keeps_the_qualification_for_the_lot_the_route_cannot_value(
    tmp_path: Path, command: object, lot: str
) -> None:
    ledger = MIXED.replace("10 HOOL {90 EUR}", lot)

    (line,) = _summary(tmp_path, ledger, *command("Assets:Hold", "2024-02"))  # type: ignore[operator]

    assert line.startswith(DATED)
    assert "only lots held at a cost in USD are valued" in line
    assert "the others still need a direct HOOL → EUR price" in line


def test_an_account_whose_every_lot_takes_the_route_has_no_qualification(tmp_path: Path) -> None:
    ledger = MIXED.replace('2024-01-03 * "EUR-cost lot"\n  Assets:Hold 10 HOOL {90 EUR}\n  Assets:Cash -900 EUR\n', "")

    assert _summary(tmp_path, ledger, *_balance("Assets:Hold", "2024-02")) == [DATED]
