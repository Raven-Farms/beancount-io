"""A bulk total cost without a currency names the field (w5/384).

`{"number_total": "1500"}` rendered `{# 1500}`, which Beancount cannot parse,
and the row was refused as "a line break or a value that is not one token".
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Brk\n2026-01-01 open Assets:Cash USD\n'


def _row(cost: dict[str, str]) -> list[dict[str, object]]:
    return [
        {
            "date": "2026-01-03",
            "narration": "b",
            "postings": [
                {"account": "Assets:Brk", "units": {"number": "10", "currency": "AAPL"}, "cost": cost},
                {"account": "Assets:Cash", "amount": "-1500 USD"},
            ],
        }
    ]


def _add(tmp_path: Path, rows: list[dict[str, object]], *flags: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "rows.json").write_text(json.dumps(rows))
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
        [sys.executable, "-m", "cli.main", *flags, "-f", "main.bean", "add", "transactions", "--from", "rows.json"],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize("json_mode", [False, True], ids=["text", "json"])
def test_a_total_cost_without_a_currency_names_the_field(tmp_path: Path, json_mode: bool) -> None:
    result = _add(tmp_path, _row({"number_total": "1500"}), *(["--json"] if json_mode else []))

    assert result.returncode == 1, result.stdout + result.stderr
    text = result.stderr
    if json_mode:
        error = json.loads(result.stderr)["error"]
        text = " ".join([error["message"], *error.get("details", [])])
    assert 'Row 1, postings.0.cost: Value error, a total cost needs "currency"' in text
    assert "not one token" not in text
    assert (tmp_path / "main.bean").read_text() == LEDGER


@pytest.mark.parametrize(
    "cost", [{"number": "150"}, {"number_total": "1500", "currency": "USD"}], ids=["per-unit", "total-with-currency"]
)
def test_costs_beancount_can_read_still_write(tmp_path: Path, cost: dict[str, str]) -> None:
    result = _add(tmp_path, _row(cost))

    assert result.returncode == 0, result.stderr
    assert "10 AAPL {" in (tmp_path / "main.bean").read_text()
