"""`add pad` before an assertion that already holds names it (w5/299).

The refusal said "omit --pad-from and add the balance alone", an option
`add pad` does not have, for a balance that already exists, and every
Unused Pad hint ran straight on from Beancount's `Unused Pad entry`.
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
2026-01-01 open Assets:Checking USD
2026-01-01 open Equity:Opening USD
2026-01-02 * "Open"
  Assets:Checking  100.00 USD
  Equity:Opening

2026-01-10 balance Assets:Checking  100.00 USD
"""


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(LEDGER)
    return path


def _add_pad(ledger: Path, date: str, *flags: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(ledger.parent / "config"),
        XDG_CACHE_HOME=str(ledger.parent / "cache"),
        XDG_DATA_HOME=str(ledger.parent / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    args = ["add", "pad", "--date", date, "-a", "Assets:Checking", "--source", "Equity:Opening"]
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", *flags, "-f", str(ledger), *args],
        env=env,
        cwd=ledger.parent,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def test_text_names_the_assertion_that_already_holds(ledger: Path) -> None:
    result = _add_pad(ledger, "2026-01-05")
    assert result.returncode == 1, result.stderr
    message = " ".join(result.stderr.split())
    assert "Unused Pad entry. The 2026-01-10 assertion at " in message
    assert "main.bean:8 already holds" in message
    assert "--pad-from" not in message
    assert ledger.read_text() == LEDGER


def test_json_carries_the_same_hint(ledger: Path) -> None:
    result = _add_pad(ledger, "2026-01-05", "--json")
    assert result.returncode == 1, result.stderr
    error = json.loads(result.stdout or result.stderr)["error"]
    text = json.dumps(error)
    assert "main.bean:8 already holds" in text
    assert "--pad-from" not in text


def test_a_lone_pad_keeps_the_atomic_hint_with_a_sentence_break(ledger: Path) -> None:
    result = _add_pad(ledger, "2026-01-15")
    assert result.returncode == 1, result.stderr
    assert "Unused Pad entry. Add both directives atomically" in " ".join(result.stderr.split())
