"""A transfer imported from both banks is reviewed on the second side, however each bank words it (w5/600).

Possible duplicates needed the same payee or narration, so "TRANSFER TO
SAVINGS" and "TRANSFER FROM CHECKING" were both booked, exit 0, and one
200 USD transfer moved each account by 400. An entry another account's import
wrote that posts this row's amount here within three days is now a possible
duplicate, whatever the description.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = (
    'option "operating_currency" "USD"\n'
    "2026-01-01 open Assets:Checking USD\n"
    "2026-01-01 open Assets:Savings USD\n"
    "2026-01-01 open Expenses:Uncategorized USD\n"
)
MAPPING = "date=Date,narration=Description,amount=Amount"
SIDES = {
    "Assets:Checking": ("c", "TRANSFER TO SAVINGS", "-200.00", "transfer to savings", "Assets:Savings"),
    "Assets:Savings": ("s", "TRANSFER FROM CHECKING", "200.00", "transfer from checking", "Assets:Checking"),
}


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER)
    for name, description, amount, match, counter in SIDES.values():
        (tmp_path / f"{name}.csv").write_text(f"Date,Description,Amount\n2026-04-10,{description},{amount}\n")
        (tmp_path / f"{name}.toml").write_text(f'[[rule]]\nmatch = "{match}"\naccount = "{counter}"\n')
    return tmp_path


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "--no-input", "--file", str(books / "main.bean"), *args],
        cwd=books,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
        check=False,
    )


def _import(books: Path, account: str, *flags: str) -> tuple[int, list[dict[str, Any]]]:
    name = SIDES[account][0]
    result = _bea(
        books, "import", f"{name}.csv", "--csv", MAPPING, "--account", account, "--rules", f"{name}.toml", *flags
    )
    payload = json.loads(result.stdout or result.stderr)
    data = payload["data"] if "data" in payload else payload["error"]["result"]
    return result.returncode, list(data["rows"])


def _balance(books: Path, account: str) -> str:
    result = _bea(books, "query", f"SELECT sum(number) WHERE account = '{account}'")
    assert result.returncode == 0, result.stderr
    return str(json.loads(result.stdout)["data"]["rows"][0][0])


@pytest.mark.parametrize("first", sorted(SIDES))
def test_the_second_side_of_a_transfer_is_reviewed_in_either_order(books: Path, first: str) -> None:
    (second,) = set(SIDES) - {first}
    assert _import(books, first, "--apply")[0] == 0
    before = (books / "main.bean").read_bytes()

    code, (row,) = _import(books, second, "--apply")

    assert code == 4
    assert row["status"] == "possible_duplicate"
    assert f"A transfer from {first} dated the same day already posts" in row["reason"]
    assert "this row may be its other side" in row["reason"]
    assert (books / "main.bean").read_bytes() == before

    assert _import(books, second, "--apply", "--duplicates", "skip")[0] == 0
    assert (_balance(books, "Assets:Checking"), _balance(books, "Assets:Savings")) == ("-200.00", "200.00")


def test_a_side_posted_over_a_weekend_is_still_paired(books: Path) -> None:
    (books / "s.csv").write_text("Date,Description,Amount\n2026-04-13,TRANSFER FROM CHECKING,200.00\n")
    assert _import(books, "Assets:Checking", "--apply")[0] == 0

    code, (row,) = _import(books, "Assets:Savings")

    assert code == 0
    assert row["status"] == "possible_duplicate"
    assert "dated 3 days earlier" in row["reason"]


def test_the_same_amount_a_week_later_is_a_new_row(books: Path) -> None:
    (books / "s.csv").write_text("Date,Description,Amount\n2026-04-17,MOBILE DEPOSIT,200.00\n")
    assert _import(books, "Assets:Checking", "--apply")[0] == 0

    code, (row,) = _import(books, "Assets:Savings", "--apply")

    assert code == 0
    assert row["status"] == "new"
    assert _balance(books, "Assets:Savings") == "400.00"
