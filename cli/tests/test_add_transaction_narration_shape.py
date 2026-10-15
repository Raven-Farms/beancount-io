"""A date in `add transaction`'s narration slot is refused, not dated today (w5/443).

`bea add transaction 2026-01-05 -p …` wrote `<today> * "2026-01-05"` with
exit 0; an account or an amount in that slot was written the same way.
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
"""
POSTINGS = ["-p", "Expenses:Food 5 USD", "-p", "Assets:Cash"]


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
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


@pytest.mark.parametrize(
    ("narration", "suggested"),
    [("2026-01-05", "2026-01-05"), ("2026/1/5", "2026-01-05"), ("01/05/2026", "YYYY-MM-DD")],
)
def test_a_date_narration_without_date_is_refused(tmp_path: Path, narration: str, suggested: str) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    result = _bea(tmp_path, "--json", "add", "transaction", narration, *POSTINGS)
    assert result.returncode == 2, result.stderr
    message = json.loads(result.stderr)["error"]["message"]
    assert f"{narration!r} looks like a date" in message
    assert f"Pass --date {suggested}" in message
    assert (tmp_path / "main.bean").read_text() == LEDGER


@pytest.mark.parametrize("narration", ["Lunch 2026-01-05", "2026-01-05"])
def test_an_explicit_date_keeps_the_narration(tmp_path: Path, narration: str) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    result = _bea(tmp_path, "add", "transaction", narration, "--date", "2026-01-05", *POSTINGS)
    assert result.returncode == 0, result.stderr
    assert f'2026-01-05 * "{narration}"' in (tmp_path / "main.bean").read_text()
    assert "looks like" not in result.stderr


@pytest.mark.parametrize(
    ("args", "shape"),
    [
        (["Expenses:Food", *POSTINGS], "an account"),
        (["5 USD", "-p", "Expenses:Food", "-p", "Assets:Cash -5 USD"], "an amount"),
        (["-p", "Expenses:Food", "5", "-p", "Assets:Cash -5 USD"], "an amount"),
    ],
)
def test_an_account_or_amount_narration_is_written_with_a_warning(tmp_path: Path, args: list[str], shape: str) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    result = _bea(tmp_path, "--json", "add", "transaction", *args)
    assert result.returncode == 0, result.stderr
    warnings = json.loads(result.stdout)["data"]["warnings"]
    assert any(f"looks like {shape}. Postings go in -p" in warning for warning in warnings), warnings


def test_an_ordinary_narration_has_no_warning(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    result = _bea(tmp_path, "add", "transaction", "Lunch", *POSTINGS)
    assert result.returncode == 0, result.stderr
    assert "looks like" not in result.stderr
