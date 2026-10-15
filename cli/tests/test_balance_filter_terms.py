"""`bea balance` keeps several filter terms apart from one term with a space (w5/341).

`account_filter` joined the terms with spaces, so `balance food cash` (two
terms, two accounts) and `balance "food cash"` (one term, nothing) both read
`"food cash"`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD
2026-01-05 * "Diner"
  Expenses:Food  12.00 USD
  Assets:Cash
"""


def _balance(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args[:1], "-f", "main.bean", "balance", *args[1:]],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize(
    ("terms", "listed", "empty"),
    [(["food", "cash"], ["food", "cash"], False), (["food cash"], ["food cash"], True)],
    ids=["two-terms", "one-term"],
)
def test_json_lists_each_term(tmp_path: Path, terms: list[str], listed: list[str], empty: bool) -> None:
    result = _balance(tmp_path, "--json", *terms)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)["data"]
    assert data["account_filters"] == listed
    assert data["account_filter_empty"] is empty


def test_text_quotes_each_term(tmp_path: Path) -> None:
    two = _balance(tmp_path, "--no-input", "food", "cash")
    assert "account: 'food' or 'cash'" in two.stdout
    one = _balance(tmp_path, "--no-input", "food cash")
    assert "No accounts match food cash." in one.stdout + one.stderr
    assert "'food cash'" not in one.stdout + one.stderr
