"""Parser diagnostics name the offending value as ledger text, not a grammar repr (w5/334).

Upstream formats a `CompoundAmount`, `KeyValue`, `TagsLinks` or a list with
`str()`, so `check` details, strict-read refusals and the `add` posting refusal
carried `Decimal('101.00')`, `datetime.date(...)` and `links=set()`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HEADER = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Assets:Broker HOOL
2026-01-01 open Expenses:Food USD
2026-01-01 open Equity:Opening
"""
SLIPS = {
    "duplicate-cost": (
        '2026-01-03 * "Buy"\n  Assets:Broker  10 HOOL {100.00 USD, 101.00 USD}\n  Assets:Cash\n',
        "Duplicate cost: '101.00 USD'.",
    ),
    "entry-meta": (
        '2026-01-03 * "Lunch"\n  amt: 5.00\n  amt: 6.00\n  Expenses:Food  5 USD\n  Assets:Cash\n',
        "Duplicate metadata field on entry: amt: 6.00",
    ),
    "posting-meta": (
        '2026-01-03 * "Lunch"\n  Expenses:Food  5 USD\n    dt: 2026-01-01\n    dt: 2026-01-02\n  Assets:Cash\n',
        "Duplicate posting metadata field: dt: 2026-01-02",
    ),
    "stray-tag": (
        '2026-01-03 * "Lunch"\n  Expenses:Food  5 USD\n  #trip\n  Assets:Cash\n',
        "Tags or links not allowed after first Posting: #trip",
    ),
    "strings": (
        '2026-01-03 * "a" "b" "c"\n  Expenses:Food  5 USD\n  Assets:Cash\n',
        'Too many strings on transaction description: "a" "b" "c"',
    ),
}
REPRS = ("CompoundAmount(", "KeyValue(", "TagsLinks(", "Decimal(", "datetime.", "set()", "['a'")


def _bea(tmp_path: Path, ledger: str, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(ledger)
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
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def _clean(text: str) -> None:
    for repr_ in REPRS:
        assert repr_ not in text, text


@pytest.mark.parametrize("slip", sorted(SLIPS))
def test_check_details_and_a_strict_read_name_the_value(tmp_path: Path, slip: str) -> None:
    body, expected = SLIPS[slip]
    check = _bea(tmp_path, HEADER + body, "--json", "check")
    assert check.returncode == 1
    details = " ".join(json.loads(check.stdout or check.stderr)["error"]["details"])
    assert expected in details
    _clean(details)
    balance = _bea(tmp_path, HEADER + body, "balance")
    assert balance.returncode == 1
    assert expected in " ".join(balance.stderr.split())
    _clean(balance.stderr)


def test_the_add_posting_refusal_names_the_cost(tmp_path: Path) -> None:
    result = _bea(
        tmp_path,
        HEADER,
        "add",
        "transaction",
        "Buy",
        "--date",
        "2026-01-03",
        "-p",
        "Assets:Broker 10 HOOL {100.00 USD, 101.00 USD}",
        "-p",
        "Assets:Cash",
    )
    assert result.returncode == 2
    assert "--posting 1: Duplicate cost: '101.00 USD'." in result.stderr
    _clean(result.stderr)
    assert (tmp_path / "main.bean").read_text() == HEADER
