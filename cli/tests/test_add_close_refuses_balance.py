"""`add close` refuses an account that still holds a balance on its close date (w2/092).

Beancount accepts such a close, and the balance then sits in a closed account:
later postings are refused and reports keep counting it. `--force` keeps the
old behavior for a deliberate close; a ledger loading `check_drained` keeps its
own plugin refusal (test_add_close_drained_hint.py).
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
2026-01-01 open Assets:Old
2026-01-01 open Assets:Old:Sub USD
2026-01-01 open Assets:Checking USD
2026-01-01 open Equity:Opening
2026-01-02 * "Seed"
  Assets:Old  100.00 USD
  Equity:Opening
"""


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _close(
    tmp_path: Path, ledger: Path, account: str, *options: str, json_out: bool = False
) -> subprocess.CompletedProcess[str]:
    global_flags = ("--json",) if json_out else ()
    return _bea(
        tmp_path,
        "-f",
        str(ledger),
        *global_flags,
        "add",
        "close",
        "--account",
        account,
        "--date",
        "2026-01-10",
        *options,
    )


@pytest.mark.parametrize("fmt", ["text", "json"])
def test_a_funded_account_is_refused_with_its_balance_and_nothing_is_written(tmp_path: Path, fmt: str) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    before = ledger.read_bytes()

    result = _close(tmp_path, ledger, "Assets:Old", json_out=fmt == "json")

    assert result.returncode == 1, result.stdout + result.stderr
    assert ledger.read_bytes() == before
    if fmt == "json":
        error = json.loads(result.stdout or result.stderr)["error"]
        assert error["category"] == "validation"
        message = error["message"]
    else:
        message = result.stderr
    assert "Assets:Old still holds 100.00 USD on 2026-01-10" in message
    assert "--force" in message
    assert "Nothing was written" in message


def test_every_remaining_currency_is_named(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER + '2026-01-03 * "Euros"\n  Assets:Old  5 EUR\n  Equity:Opening\n')

    result = _close(tmp_path, ledger, "Assets:Old")

    assert result.returncode == 1
    assert "still holds 5 EUR, 100.00 USD on 2026-01-10" in result.stderr


def test_force_closes_it_with_the_balance(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)

    result = _close(tmp_path, ledger, "Assets:Old", "--force")

    assert result.returncode == 0, result.stderr
    assert ledger.read_text().endswith("2026-01-10 close Assets:Old\n")


def test_an_account_emptied_on_the_close_date_closes(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER + '2026-01-10 * "Move out"\n  Assets:Old  -100.00 USD\n  Assets:Checking\n')

    result = _close(tmp_path, ledger, "Assets:Old")

    assert result.returncode == 0, result.stderr
    assert ledger.read_text().endswith("2026-01-10 close Assets:Old\n")


def test_a_balance_after_the_close_date_does_not_count(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(
        LEDGER.replace('2026-01-02 * "Seed"', '2026-01-11 * "Seed"')
        + '2026-01-02 * "Earlier"\n  Assets:Checking  1.00 USD\n  Equity:Opening\n'
    )

    result = _close(tmp_path, ledger, "Assets:Old", "--allow-errors")

    # Nothing is held on the close date, so the close is not refused for a
    # balance; the later posting to a closed account is the ledger's own error.
    assert "still holds" not in result.stderr


def test_a_child_account_balance_does_not_block_closing_the_parent(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER.replace("  Assets:Old  100.00 USD", "  Assets:Old:Sub  100.00 USD"))

    result = _close(tmp_path, ledger, "Assets:Old")

    assert result.returncode == 0, result.stderr
    assert ledger.read_text().endswith("2026-01-10 close Assets:Old\n")
