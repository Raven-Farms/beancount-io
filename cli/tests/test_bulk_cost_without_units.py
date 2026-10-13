"""A bulk posting with `cost` but no `units` is refused, not written without its lot (w5/212).

Beancount's printer renders nothing for a cost beside missing units, so the
row was written as a bare balancing leg and reported as one clean write: the
cost, lot date and label were gone and the account held cash instead of a lot.
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
2024-01-01 open Assets:Broker
2024-01-01 open Assets:Cash USD
"""

LOT = {"number": "100.00", "currency": "USD", "date": "2024-06-01", "label": "lot1"}


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _buy(tmp_path: Path, broker: dict[str, object], *extra: str) -> tuple[subprocess.CompletedProcess[str], Path]:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")
    rows = tmp_path / "rows.json"
    row = {
        "date": "2024-06-01",
        "narration": "buy",
        "postings": [
            {"account": "Assets:Broker", **broker},
            {"account": "Assets:Cash", "amount": "-1000.00 USD"},
        ],
    }
    rows.write_text(json.dumps([row]), encoding="utf-8")
    return _bea(tmp_path, "--json", "--file", str(ledger), "add", "transactions", "--from", str(rows), *extra), ledger


@pytest.mark.parametrize(
    "cost",
    [LOT, {"number_total": "1000.00", "currency": "USD"}, {"currency": "USD"}, {}],
    ids=["lot", "total", "currency-only", "empty"],
)
@pytest.mark.parametrize("extra", [(), ("--partial",)], ids=["strict", "partial"])
def test_cost_without_units_rejects_the_row(tmp_path: Path, cost: dict[str, object], extra: tuple[str, ...]) -> None:
    result, ledger = _buy(tmp_path, {"cost": cost}, *extra)

    assert result.returncode == 1, result.stderr or result.stdout
    error = json.loads(result.stderr)["error"]
    assert error["result"]["rejected_rows"] == [0]
    assert error["result"]["written"] == 0
    refusals = [detail for detail in error["details"] if "cost on a posting without units" in detail]
    assert len(refusals) == 1
    assert refusals[0].startswith("Row 1, postings.0:")
    assert ledger.read_text(encoding="utf-8") == LEDGER


@pytest.mark.parametrize(
    "units",
    [{"units": {"number": "10", "currency": "HOOL"}}, {"amount": "10 HOOL"}],
    ids=["units", "amount"],
)
def test_the_same_posting_with_units_keeps_its_cost_date_and_label(tmp_path: Path, units: dict[str, object]) -> None:
    result, ledger = _buy(tmp_path, {**units, "cost": LOT})

    assert result.returncode == 0, result.stderr or result.stdout
    assert json.loads(result.stdout)["data"] == {"written": 1, "rejected": []}
    appended = ledger.read_text(encoding="utf-8")[len(LEDGER) :]
    assert 'Assets:Broker        10 HOOL {100.00 USD, 2024-06-01, "lot1"}' in appended

    check = _bea(tmp_path, "--json", "--file", str(ledger), "check")
    assert check.returncode == 0, check.stderr or check.stdout


def test_a_plain_balancing_posting_is_still_written(tmp_path: Path) -> None:
    result, ledger = _buy(tmp_path, {})

    assert result.returncode == 0, result.stderr or result.stdout
    appended = ledger.read_text(encoding="utf-8")[len(LEDGER) :]
    assert "  Assets:Broker\n" in appended


def test_a_loaded_posting_is_never_refused() -> None:
    """Only a write is held to the rule; a listing must not fail on a generated entry."""
    script = (
        "from bea_engine.ledger.models import WRITE_INPUT, Posting\n"
        "from pydantic import ValidationError\n"
        "row = {'account': 'Assets:Broker', 'cost': {'currency': 'USD'}}\n"
        "assert Posting.model_validate(row).cost is not None\n"
        "try:\n"
        "    Posting.model_validate(row, context=WRITE_INPUT)\n"
        "except ValidationError as exc:\n"
        "    assert 'cost on a posting without units' in str(exc)\n"
        "else:\n"
        "    raise SystemExit('a write was not refused')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        env=os.environ | {"PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr or result.stdout
