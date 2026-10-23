"""A reciprocal pair settles per day, ties canonically, quotes stay exact (w5/740).

Whole-ledger settlement let a March quote flip January's valuation, broke
ties by line number (even across include files, where Beancount sorts
without the file name), and double-inverted originals into 1e-26 residue in
JSON. Each day now settles from the quotes up to that day, a tie favors the
quote from the alphabetically later currency, and the winning quote stays
exact in its own direction — in reports and in BQL alike.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADER = """option "operating_currency" "USD"
2026-01-01 open Assets:EUR EUR
2026-01-01 open Equity:Opening
2026-01-02 * "Fund"
  Assets:EUR  1000.00 EUR
  Equity:Opening
"""
PAIR = "2026-01-05 price EUR 1.20 USD\n2026-01-05 price USD 0.80 EUR\n"
SWAPPED = "2026-01-05 price USD 0.80 EUR\n2026-01-05 price EUR 1.20 USD\n"
MARCH = "2026-03-01 price USD 0.70 EUR\n"
JANUARY_CONVERT = "SELECT convert(sum(position), 'USD', DATE('2026-01-31')) AS v WHERE account = 'Assets:EUR'"


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "--file", str(tmp_path / "main.bean"), *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _data(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["data"]


def test_a_later_quote_does_not_value_an_earlier_month(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(HEADER + PAIR, encoding="utf-8")
    january = _data(_bea(tmp_path, "balance", "Assets:EUR", "--time", "2026-01"))
    assert "1250.00" in json.dumps(january), january

    (tmp_path / "main.bean").write_text(HEADER + PAIR + MARCH, encoding="utf-8")
    january = _data(_bea(tmp_path, "balance", "Assets:EUR", "--time", "2026-01"))
    assert "1250.00" in json.dumps(january), january

    query = _data(_bea(tmp_path, "query", JANUARY_CONVERT))
    assert json.dumps(query["rows"]).count("1250.0000") == 1, query["rows"]


def test_a_tie_ignores_line_and_file_order(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(HEADER + SWAPPED, encoding="utf-8")
    swapped = _data(_bea(tmp_path, "balance", "Assets:EUR", "--time", "2026-01"))
    assert "1250.00" in json.dumps(swapped), swapped

    (tmp_path / "main.bean").write_text(HEADER + 'include "a.bean"\ninclude "b.bean"\n', encoding="utf-8")
    (tmp_path / "a.bean").write_text("2026-01-05 price EUR 1.20 USD\n", encoding="utf-8")
    (tmp_path / "b.bean").write_text("\n\n\n2026-01-05 price USD 0.80 EUR\n", encoding="utf-8")
    split = _data(_bea(tmp_path, "balance", "Assets:EUR", "--time", "2026-01"))
    assert "1250.00" in json.dumps(split), split


def test_original_quotes_stay_exact(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(
        """option "operating_currency" "EUR"
2026-01-01 open Assets:USD USD
2026-01-01 open Assets:EUR EUR
2026-01-01 open Equity:Opening
2026-01-05 price EUR 1.10 USD
2026-01-05 price EUR 1.10 USD
2026-01-05 * "Buy"
  Assets:USD  100.00 USD @ 0.90 EUR
  Equity:Opening
2026-01-05 price USD 0.90 EUR
""",
        encoding="utf-8",
    )

    sheet = _data(_bea(tmp_path, "report", "balance-sheet"))

    assert sheet["net_worth"] == {"EUR": "90.0000"}, sheet["net_worth"]
    assert sheet["valuation_adjustment"] == {"EUR": "0"}, sheet["valuation_adjustment"]


def test_a_chain_of_ties_is_deterministic(tmp_path: Path) -> None:
    header = """option "operating_currency" "USD"
2026-01-01 open Assets:Inv EUR
2026-01-01 open Assets:Cash USD
2026-01-01 open Equity:Opening
2026-01-02 * "Buy"
  Assets:Inv  1000.00 EUR {0.80 USD}
  Assets:Cash  -800.00 USD
"""
    first = (
        "2026-01-05 price EUR 1.20 USD\n"
        "2026-01-05 price USD 0.80 EUR\n"
        "2026-01-05 price USD 150.00 JPY\n"
        "2026-01-05 price JPY 0.006 USD\n"
    )
    reversed_quotes = "".join(reversed(first.splitlines(keepends=True)))

    (tmp_path / "main.bean").write_text(header + first, encoding="utf-8")
    one = _data(_bea(tmp_path, "balance", "Assets:Inv", "--conversion", "JPY", "--time", "2026-01"))
    (tmp_path / "main.bean").write_text(header + reversed_quotes, encoding="utf-8")
    two = _data(_bea(tmp_path, "balance", "Assets:Inv", "--conversion", "JPY", "--time", "2026-01"))

    assert "187500.00" in json.dumps(one), one
    assert "187500.00" in json.dumps(two), two
