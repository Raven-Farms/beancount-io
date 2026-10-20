"""A transfer is the other side of one row only, the one dated nearest it (w5/821).

One transfer from checking was offered as the other side of every
same-amount savings row within three days, so a real deposit beside it was a
possible duplicate too: `--duplicates skip` lost the deposit, and `include`
booked the transfer twice.
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
    "2026-01-01 open Income:Gifts USD\n"
)
MAPPING = "date=Date,narration=Description,amount=Amount"


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "c.csv").write_text("Date,Description,Amount\n2026-04-10,TRANSFER TO SAVINGS,-200.00\n")
    (tmp_path / "c.toml").write_text('[[rule]]\nmatch = "transfer to savings"\naccount = "Assets:Savings"\n')
    (tmp_path / "s.toml").write_text(
        '[[rule]]\nmatch = "transfer from checking"\naccount = "Assets:Checking"\n'
        '[[rule]]\nmatch = "zelle from mom"\naccount = "Income:Gifts"\n'
    )
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


def _import(books: Path, name: str, account: str, *flags: str) -> tuple[int, list[dict[str, Any]]]:
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


@pytest.mark.parametrize("deposit_first", [False, True], ids=["transfer-row-first", "deposit-row-first"])
def test_a_deposit_beside_a_transfer_is_new_and_skip_keeps_it(books: Path, deposit_first: bool) -> None:
    assert _import(books, "c", "Assets:Checking", "--apply")[0] == 0
    rows = ["2026-04-10,TRANSFER FROM CHECKING,200.00", "2026-04-11,ZELLE FROM MOM,200.00"]
    (books / "s.csv").write_text("Date,Description,Amount\n" + "\n".join(rows[::-1] if deposit_first else rows) + "\n")

    code, preview = _import(books, "s", "Assets:Savings")

    assert code == 0
    statuses = {row["narration"]: row["status"] for row in preview}
    assert statuses == {"TRANSFER FROM CHECKING": "possible_duplicate", "ZELLE FROM MOM": "new"}

    code, _ = _import(books, "s", "Assets:Savings", "--apply", "--duplicates", "skip")

    assert code == 0
    assert (_balance(books, "Assets:Checking"), _balance(books, "Assets:Savings")) == ("-200.00", "400.00")
