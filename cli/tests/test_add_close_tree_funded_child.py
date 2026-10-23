"""`add close` judges the descendants `close_tree` closes with the account (w5/910).

Only the requested parent was checked for a balance, so closing an empty
parent also closed its funded child, exit 0, and the child's clearing
transaction was then refused as inactive.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_add_close_drained_uncovered import _bea

LEDGER = """option "operating_currency" "USD"
2024-01-01 open Assets:Bank
2024-01-01 open Assets:Bank:Checking USD
2024-01-01 open Equity:Opening USD
2024-01-02 * "Fund"
  Assets:Bank:Checking 100 USD
  Equity:Opening -100 USD
"""
TREE = 'plugin "beancount.plugins.close_tree"\n'


def _close(tmp_path: Path, ledger: str, *flags: str) -> tuple[object, bytes]:
    path = tmp_path / "main.bean"
    path.write_text(ledger)
    before = path.read_bytes()
    result = _bea(
        tmp_path, "--json", "-f", str(path), "add", "close", "--account", "Assets:Bank", "--date", "2024-02-01", *flags
    )
    return result, before


def test_a_funded_child_refuses_the_unforced_close(tmp_path: Path) -> None:
    result, before = _close(tmp_path, TREE + LEDGER)

    assert result.returncode == 1, result.stdout  # type: ignore[attr-defined]
    message = " ".join(json.loads(result.stderr)["error"]["message"].split())  # type: ignore[attr-defined]
    assert "Assets:Bank:Checking still holds 100 USD" in message
    assert "close_tree plugin closes it with Assets:Bank" in message and "--force" in message
    assert (tmp_path / "main.bean").read_bytes() == before


def test_force_closes_both_deliberately(tmp_path: Path) -> None:
    result, _ = _close(tmp_path, TREE + LEDGER, "--force")

    assert result.returncode == 0, result.stderr  # type: ignore[attr-defined]


def test_without_the_plugin_the_parent_closes_alone(tmp_path: Path) -> None:
    result, _ = _close(tmp_path, LEDGER)

    assert result.returncode == 0, result.stderr  # type: ignore[attr-defined]


def test_a_drained_child_closes_with_its_parent(tmp_path: Path) -> None:
    drained = LEDGER + '2024-01-31 * "Move"\n  Assets:Bank:Checking -100 USD\n  Equity:Opening 100 USD\n'

    result, _ = _close(tmp_path, TREE + drained)

    assert result.returncode == 0, result.stderr  # type: ignore[attr-defined]


def test_a_child_with_its_own_close_is_not_judged_again(tmp_path: Path) -> None:
    result, _ = _close(tmp_path, TREE + LEDGER + "2024-01-15 close Assets:Bank:Checking\n")

    assert result.returncode == 0, result.stderr  # type: ignore[attr-defined]


def test_a_funded_parent_keeps_its_own_wording(tmp_path: Path) -> None:
    funded = LEDGER.replace("Assets:Bank:Checking 100 USD", "Assets:Bank 100 USD")

    result, before = _close(tmp_path, TREE + funded)

    assert result.returncode == 1, result.stdout  # type: ignore[attr-defined]
    message = " ".join(json.loads(result.stderr)["error"]["message"].split())  # type: ignore[attr-defined]
    assert message.startswith("Assets:Bank still holds 100 USD on 2024-02-01. Move that balance out of Assets:Bank")
    assert (tmp_path / "main.bean").read_bytes() == before


@pytest.mark.parametrize("plugin", [TREE])
def test_a_later_clearing_transaction_is_possible_after_the_refusal(tmp_path: Path, plugin: str) -> None:
    _close(tmp_path, plugin + LEDGER)

    cleared = _bea(
        tmp_path, "--json", "-f", str(tmp_path / "main.bean"), "add", "transaction", "Move funds",
        "--date", "2024-02-02", "-p", "Assets:Bank:Checking -100 USD", "-p", "Equity:Opening 100 USD",
    )  # fmt: skip

    assert cleared.returncode == 0, cleared.stderr
