"""A holding worth exactly zero shows `0 USD`, not an empty account (w5/908).

A nonempty position that converts to zero (a zero quote, a stated zero cost)
was reduced into an inventory that drops zeros, so its currency was lost and
the tree read `—` / `{}` as if the account held nothing, beside a headline
that correctly said 0.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.test_import_source_facts import _bea

HEAD = 'option "operating_currency" "USD"\n2024-01-01 open Assets:Stock HOOL\n2024-01-01 open Assets:Cash USD\n'
ZERO_PRICED = (
    HEAD
    + '2024-02-01 * "Holding"\n  Assets:Stock 2 HOOL {100 USD}\n  Assets:Cash -200 USD\n2024-02-02 price HOOL 0 USD\n'
)
ZERO_COST = (
    HEAD + '2024-02-01 * "Grant"\n  Assets:Stock 2 HOOL {0 USD}\n  Assets:Cash 0 USD\n2024-02-02 price HOOL 10 USD\n'
)
PRICED = (
    HEAD
    + '2024-02-01 * "Holding"\n  Assets:Stock 2 HOOL {100 USD}\n  Assets:Cash -200 USD\n2024-02-02 price HOOL 10 USD\n'
)


def _node(tree: dict[str, Any] | None, account: str) -> dict[str, Any] | None:
    if tree is None:
        return None
    if tree["account"] == account:
        return tree
    for child in tree["children"]:
        found = _node(child, account)
        if found is not None:
            return found
    return None


def _stock(tmp_path: Path, ledger: str, conversion: str, *command: str) -> dict[str, Any]:
    (tmp_path / "main.bean").write_text(ledger)
    result = _bea(tmp_path, *command, "-t", "2024-02", "-x", conversion)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)["data"]
    node = _node(data["assets"], "Assets:Stock")
    assert node is not None
    return node


COMMANDS = [("balance", "Assets:Stock"), ("report", "balance-sheet", "--account", "Assets:Stock")]


@pytest.mark.parametrize("command", COMMANDS, ids=["balance", "balance-sheet"])
@pytest.mark.parametrize(
    ("ledger", "conversion"),
    [(ZERO_PRICED, "USD"), (ZERO_PRICED, "at_value"), (ZERO_COST, "at_cost")],
    ids=["usd", "value", "cost"],
)
def test_a_position_worth_zero_reads_zero_in_its_currency(
    tmp_path: Path, command: tuple[str, ...], ledger: str, conversion: str
) -> None:
    node = _stock(tmp_path, ledger, conversion, *command)

    assert node["has_txns"] is True
    assert {k: float(v) for k, v in node["balance"].items()} == {"USD": 0.0}
    assert {k: float(v) for k, v in node["balance_children"].items()} == {"USD": 0.0}


@pytest.mark.parametrize("command", COMMANDS, ids=["balance", "balance-sheet"])
def test_the_nonzero_conversions_are_unchanged(tmp_path: Path, command: tuple[str, ...]) -> None:
    at_value = _stock(tmp_path, PRICED, "USD", *command)
    at_cost = _stock(tmp_path, PRICED, "at_cost", *command)
    units = _stock(tmp_path, ZERO_COST, "units", *command)

    assert {k: float(v) for k, v in at_value["balance"].items()} == {"USD": 20.0}
    assert {k: float(v) for k, v in at_cost["balance"].items()} == {"USD": 200.0}
    assert {k: float(v) for k, v in units["balance"].items()} == {"HOOL": 2.0}


def test_an_account_with_no_holding_stays_empty(tmp_path: Path) -> None:
    node = _stock(tmp_path, HEAD + "2024-02-02 price HOOL 10 USD\n", "USD", "balance", "Assets:Stock")

    assert node["balance"] == {} and node["balance_children"] == {}
