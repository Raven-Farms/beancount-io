"""A plain `add balance` refuses a gap a non-staged pad would silently pad (w5/796).

Upstream keeps a pad active for every currency it has not yet padded, so a
pad consumed by an earlier assertion still pads a new currency's gap without
a word — a wrong statement balance exits 0 and backdates an adjustment. The
plain path now refuses, naming the pad and the amount it would insert. A
staged pad still completes silently, and `--pad-from`/`--force` opt in.
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
2026-01-01 open Assets:Checking
2026-01-01 open Equity:OpeningBalances
2026-01-05 * "Deposit"
  Assets:Checking  1000.00 USD
  Equity:OpeningBalances
2026-01-06 * "Euros"
  Assets:Checking  200.00 EUR
  Equity:OpeningBalances
2026-01-09 pad Assets:Checking Equity:OpeningBalances
2026-01-10 balance Assets:Checking   1100.00 USD
"""


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    path = tmp_path / "mc.bean"
    path.write_text(LEDGER)
    return path


def _add(ledger: Path, *args: str, as_json: bool = False) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(ledger.parent / "config"),
        XDG_CACHE_HOME=str(ledger.parent / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    command = [sys.executable, "-m", "cli.main"]
    if as_json:
        command.append("--json")
    return subprocess.run(
        [*command, "--no-input", "--file", str(ledger), *args],
        env=env,
        cwd=ledger.parent,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def test_used_pad_fill_is_refused_naming_pad_and_amount(ledger: Path) -> None:
    before = ledger.read_bytes()

    result = _add(ledger, "add", "balance", "--date", "2026-03-15", "-a", "Assets:Checking", "--amount", "250.00 EUR")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "2026-01-09" in result.stderr
    assert "50.00 EUR" in result.stderr
    assert "Nothing was written" in result.stderr
    assert ledger.read_bytes() == before


def test_refusal_is_reported_in_json(ledger: Path) -> None:
    result = _add(
        ledger,
        "add",
        "balance",
        "--date",
        "2026-03-15",
        "-a",
        "Assets:Checking",
        "--amount",
        "250.00 EUR",
        as_json=True,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    error = json.loads(result.stderr)["error"]
    assert (error["category"], error["exit_code"]) == ("validation", 1)
    assert "2026-01-09" in error["message"] and "50.00 EUR" in error["message"]


def test_staged_pad_two_step_still_writes(tmp_path: Path) -> None:
    ledger = tmp_path / "fresh.bean"
    ledger.write_text(
        'option "operating_currency" "USD"\n'
        "2026-01-01 open Assets:Checking\n"
        "2026-01-01 open Equity:OpeningBalances\n"
        '2026-01-05 * "Deposit"\n'
        "  Assets:Checking  1000.00 USD\n"
        "  Equity:OpeningBalances\n"
    )
    staged = _add(
        ledger,
        "add",
        "pad",
        "--date",
        "2026-03-01",
        "-a",
        "Assets:Checking",
        "-s",
        "Equity:OpeningBalances",
        "--allow-errors",
    )
    assert staged.returncode == 0, staged.stderr

    result = _add(ledger, "add", "balance", "--date", "2026-03-15", "-a", "Assets:Checking", "--amount", "900.00 USD")

    assert result.returncode == 0, result.stderr
    assert "Added 1 balance to " in result.stdout


def test_consumed_currency_fails_naturally(ledger: Path) -> None:
    exact = _add(ledger, "add", "balance", "--date", "2026-02-01", "-a", "Assets:Checking", "--amount", "200.00 EUR")
    assert exact.returncode == 0, exact.stderr

    result = _add(ledger, "add", "balance", "--date", "2026-03-15", "-a", "Assets:Checking", "--amount", "250.00 EUR")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Balance failed" in result.stderr
    assert "would silently insert" not in result.stderr


def test_exact_assertion_with_a_used_pad_writes(ledger: Path) -> None:
    result = _add(ledger, "add", "balance", "--date", "2026-03-15", "-a", "Assets:Checking", "--amount", "200.00 EUR")

    assert result.returncode == 0, result.stderr


def test_pad_from_opts_in_with_the_pad_source(ledger: Path) -> None:
    result = _add(
        ledger,
        "add",
        "balance",
        "--date",
        "2026-03-15",
        "-a",
        "Assets:Checking",
        "--amount",
        "250.00 EUR",
        "--pad-from",
        "Equity:OpeningBalances",
    )

    assert result.returncode == 0, result.stderr


def test_force_records_the_padded_assertion(ledger: Path) -> None:
    result = _add(
        ledger, "add", "balance", "--date", "2026-03-15", "-a", "Assets:Checking", "--amount", "250.00 EUR", "--force"
    )

    assert result.returncode == 0, result.stderr
