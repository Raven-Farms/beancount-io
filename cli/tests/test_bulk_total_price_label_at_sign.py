"""A lot label holding ` @ ` survives a bulk row's `@@` total price (w5/211)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2024-01-01 open Assets:Broker
2024-01-01 open Assets:Cash USD
"""
PLAIN = {
    "date": "2024-06-01",
    "narration": "plain",
    "postings": [{"account": "Assets:Broker", "amount": "1 ABC {10 USD}"}, {"account": "Assets:Cash"}],
}


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    file = tmp_path / "main.bean"
    file.write_text(LEDGER)
    return file


def _bea(tmp_path: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
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
        capture_output=True,
        text=True,
        timeout=30,
        **({"stdin": subprocess.DEVNULL} if stdin is None else {"input": stdin}),
    )


def _structured(label: str) -> dict[str, Any]:
    return {
        "date": "2024-06-02",
        "narration": "labelled, total price",
        "postings": [
            {
                "account": "Assets:Broker",
                "units": {"number": "10", "currency": "ABC"},
                "cost": {"number": "10", "currency": "USD", "label": label},
                "price_total": {"number": "121", "currency": "USD"},
            },
            {"account": "Assets:Cash"},
        ],
    }


def _shorthand(label: str) -> dict[str, Any]:
    return {
        "date": "2024-06-02",
        "narration": "labelled, total price",
        "postings": [
            {"account": "Assets:Broker", "amount": f'10 ABC {{10 USD, "{label}"}} @@ 121 USD'},
            {"account": "Assets:Cash"},
        ],
    }


@pytest.mark.parametrize("row", [_structured, _shorthand], ids=["structured", "shorthand"])
@pytest.mark.parametrize("label", ["AAPL @ Schwab", "a @ b @ c", "AAPL at Schwab"], ids=["at-sign", "two", "control"])
def test_bulk_total_price_keeps_a_label_with_an_at_sign(ledger: Path, row: Any, label: str) -> None:
    rows = ledger.parent / "rows.json"
    rows.write_text(json.dumps([PLAIN, row(label)]))

    result = _bea(ledger.parent, "--file", str(ledger), "add", "transactions", "--from", str(rows))

    assert result.returncode == 0, result.stderr
    assert ledger.read_text()[len(LEDGER) :] == (
        '\n2024-06-01 * "plain"\n'
        "  Assets:Broker   1 ABC {10 USD}\n"
        "  Assets:Cash\n"
        '\n2024-06-02 * "labelled, total price"\n'
        f'  Assets:Broker  10 ABC {{10 USD, "{label}"}} @@ 121 USD\n'
        "  Assets:Cash\n"
    )


def test_flag_answer_with_an_at_sign_label_round_trips_through_bulk(ledger: Path) -> None:
    added = _bea(
        ledger.parent,
        *("--json", "--file", str(ledger), "add", "transaction", "single", "--date", "2024-06-02"),
        *("--posting", 'Assets:Broker 10 ABC {10 USD, "AAPL @ Schwab"} @@ 121 USD', "--posting", "Assets:Cash"),
    )
    assert added.returncode == 0, added.stderr
    first = ledger.read_text()[len(LEDGER) :]
    assert '  Assets:Broker  10 ABC {10 USD, "AAPL @ Schwab"} @@ 121 USD\n' in first
    directive = json.loads(added.stdout)["data"]["directive"]

    ledger.write_text(LEDGER)
    bulk = _bea(
        ledger.parent, "--file", str(ledger), "add", "transactions", "--from", "-", stdin=json.dumps([directive])
    )

    assert bulk.returncode == 0, bulk.stderr
    assert ledger.read_text()[len(LEDGER) :] == first
