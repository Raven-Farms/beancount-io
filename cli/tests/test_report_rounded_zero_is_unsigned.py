"""A text-report amount that rounds to zero prints without a sign (w5/217).

Net profit of 25.00 - 25.40 is -0.40, which at whole-dollar display
precision is zero. `quantize` keeps the sign, so every text report and
`bea balance` printed `-0 USD`, while the balance sheet showed the same
quantity as `0 USD` four lines away.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

PRECISION = 'option "display_precision" "USD:1"\n'
LEDGER = """\
option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Income:Interest
2026-01-01 open Expenses:Fees

2026-01-05 * "wire fee"
  Expenses:Fees     25.40 USD
  Assets:Checking

2026-01-31 * "interest"
  Assets:Checking   25.00 USD
  Income:Interest
"""
# A converted amount below the cents the ledger uses: 5 KRW is 0.0036 USD.
CONVERTED = """\
option "operating_currency" "USD"
2026-01-01 open Assets:Cash
2026-01-01 open Expenses:Snacks
2026-01-01 open Equity:Opening
2026-01-01 price KRW 0.00072 USD

2026-01-02 * "opening"
  Assets:Cash       10.00 USD
  Equity:Opening

2026-01-03 * "gum"
  Expenses:Snacks   5 KRW
  Assets:Cash
"""
NEGATIVE_ZERO = re.compile(r"-0(\.0+)? USD")


def _bea(tmp_path: Path, ledger: str, *args: str) -> str:
    (tmp_path / "main.bean").write_text(ledger, encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--file", str(tmp_path / "main.bean"), *args],
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_income_statement_rounds_net_profit_to_an_unsigned_zero(tmp_path: Path) -> None:
    out = _bea(tmp_path, PRECISION + LEDGER, "report", "income-statement", "-i", "yearly")

    assert "Net Profit: 0 USD" in out
    (row,) = [line.split() for line in out.splitlines() if line.startswith("2026-12-31")]
    assert row == ["2026-12-31", "-25", "USD", "25", "USD", "0", "USD"]
    assert not NEGATIVE_ZERO.search(out)


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (
            ("report", "balance-sheet", "-i", "yearly"),
            [r"Checking\s+0 USD", r"Net Profit is 0 USD\.", r"Net Worth: 0 USD", r"2026-12-31\s+0 USD"],
        ),
        (("report", "overview"), [r"Assets:\s+0 USD", r"Net Worth:\s+0 USD", r"2026-01-31\s+0 USD"]),
        (("report", "trial-balance"), [r"Checking\s+0 USD"]),
        (("balance",), [r"Checking\s+0 USD"]),
    ],
)
def test_every_text_report_prints_a_rounded_zero_unsigned(
    tmp_path: Path, args: tuple[str, ...], expected: list[str]
) -> None:
    out = _bea(tmp_path, PRECISION + LEDGER, *args)

    for pattern in expected:
        assert re.search(pattern, out), pattern
    assert not NEGATIVE_ZERO.search(out)


def test_converted_amount_below_the_ledger_precision_is_an_unsigned_zero(tmp_path: Path) -> None:
    out = _bea(tmp_path, CONVERTED, "report", "income-statement", "-x", "USD")

    assert re.search(r"Snacks\s+0\.00 USD", out)
    assert "Net Profit: 0.00 USD" in out
    assert not NEGATIVE_ZERO.search(out)


def test_an_amount_the_precision_can_show_keeps_its_sign(tmp_path: Path) -> None:
    out = _bea(tmp_path, LEDGER, "report", "income-statement", "-i", "yearly")

    assert "Net Profit: -0.40 USD" in out
    (row,) = [line.split() for line in out.splitlines() if line.startswith("2026-12-31")]
    assert row == ["2026-12-31", "-25.00", "USD", "25.40", "USD", "-0.40", "USD"]


def test_json_keeps_the_exact_signed_value(tmp_path: Path) -> None:
    out = _bea(tmp_path, PRECISION + LEDGER, "--json", "report", "income-statement")

    assert '"-0.40"' in json.dumps(json.loads(out))
