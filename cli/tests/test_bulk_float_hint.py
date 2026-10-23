"""A refused JSON float's hint suggests a string the same input accepts (w5/335).

The hint quoted the float's `str()`: `'1e+20'` and `'1e-08'` were then refused
as scientific notation, and `'nan'`/`'-inf'` as invalid, so following it looped.

w5/735 quotes the literal as typed instead, so an exponent literal is quoted
verbatim and refused as scientific notation when followed — the exchange
still terminates, and nothing is corrupted in between.
"""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Expenses:Food USD
2026-01-01 open Assets:Cash USD
2026-01-01 open Assets:Broker
"""


def _row(field: str, value: Any) -> dict[str, Any]:
    row: dict[str, Any] = {"date": "2026-01-05", "narration": "B"}
    if field == "units":
        row["postings"] = [
            {"account": "Expenses:Food", "units": {"number": value, "currency": "USD"}},
            {"account": "Assets:Cash"},
        ]
    elif field == "cost":
        row["postings"] = [
            {
                "account": "Assets:Broker",
                "units": {"number": "1", "currency": "HOOL"},
                "cost": {"number": value, "currency": "USD"},
            },
            {"account": "Assets:Cash"},
        ]
    else:
        row["meta"] = {"rate": {"kind": "number", "value": value}}
        row["postings"] = [
            {"account": "Expenses:Food", "units": {"number": "1", "currency": "USD"}},
            {"account": "Assets:Cash"},
        ]
    return row


def _add(tmp_path: Path, row: dict[str, Any]) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "in.json").write_text(json.dumps([row]))  # allow_nan: NaN and -Infinity as JSON literals
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
        [sys.executable, "-m", "cli.main", "-f", "main.bean", "add", "transactions", "--from", "in.json"],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize("field", ["units", "cost", "meta"])
@pytest.mark.parametrize("value", [1e20, 1e-8, math.nan, -math.inf], ids=["1e20", "1e-8", "nan", "-inf"])
def test_the_hint_is_accepted_or_withheld(tmp_path: Path, field: str, value: float) -> None:
    refused = _add(tmp_path, _row(field, value))
    message = " ".join(refused.stderr.split())
    assert refused.returncode != 0, refused.stdout
    suggestion = re.search(r"decimal string, such as '([^']*)'", message)
    if not math.isfinite(value):
        assert suggestion is None and "is not a finite number" in message
        return
    assert suggestion is not None, message
    if "e" in suggestion[1].lower():
        # An exponent literal is quoted verbatim (w5/735): following it is
        # refused as scientific notation, which names decimal notation, so
        # the exchange terminates instead of looping.
        assert suggestion[1] == f"{value}"
        followed = _add(tmp_path, _row(field, suggestion[1]))
        assert followed.returncode != 0
        if field == "meta":
            assert "no exponent or underscores" in followed.stderr
        else:
            assert "Scientific notation" in followed.stderr
            assert "Use decimal notation" in followed.stderr
        return
    accepted = _add(tmp_path, _row(field, suggestion[1]))
    assert accepted.returncode == 0, accepted.stderr
