"""The report tree escapes bidi overrides in account names, as `list` does (w5/331).

w5/148 made human output show U+202A–202E and U+2066–2069 as a visible
`\\uNNNN`, but the tree `balance` and `report` print wrote them raw, so on a
bidi-aware terminal the rest of the row could read reversed.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NAME = "Assets:Pay‮emoc"
LEDGER = f"""option "operating_currency" "USD"
2026-01-01 open {NAME} USD
2026-01-01 open Equity:Opening
2026-01-02 * "Open"
  {NAME}  5 USD
  Equity:Opening
"""


def _bea(tmp_path: Path, *args: str) -> str:
    (tmp_path / "main.bean").write_text(LEDGER, encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


@pytest.mark.parametrize("args", [("balance",), ("report", "balance-sheet")], ids=["balance", "report"])
def test_the_tree_shows_the_override_escaped(tmp_path: Path, args: tuple[str, ...]) -> None:
    out = _bea(tmp_path, *args)
    assert "‮" not in out
    row = next(line for line in out.splitlines() if "Pay\\u202eemoc" in line)
    assert row.rstrip().endswith("5 USD")


def test_json_keeps_the_exact_name(tmp_path: Path) -> None:
    assert NAME.split(":")[1] in json.dumps(json.loads(_bea(tmp_path, "--json", "balance")), ensure_ascii=False)
