"""`list transaction --flag txn` lists the `*` transactions, as `add --flag txn` writes them (w5/526)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD
2026-01-02 txn "cleared"
  Expenses:Food 5 USD
  Assets:Cash
2026-01-03 ! "pending"
  Expenses:Food 3 USD
  Assets:Cash
"""


def _list(tmp_path: Path, flag: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
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
        [sys.executable, "-m", "cli.main", "--json", "-f", str(tmp_path / "main.bean"), "list", "transaction"]
        + ["--flag", flag],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_txn_lists_the_star_transactions(tmp_path: Path) -> None:
    txn = _list(tmp_path, "txn")
    star = _list(tmp_path, "*")

    assert txn.returncode == 0, txn.stderr
    assert [row["narration"] for row in json.loads(txn.stdout)["data"]] == ["cleared"]
    assert json.loads(txn.stdout)["data"] == json.loads(star.stdout)["data"]


def test_an_unknown_flag_word_is_still_refused(tmp_path: Path) -> None:
    result = _list(tmp_path, "done")

    assert result.returncode == 2
    assert "a capital letter or txn" in result.stdout + result.stderr
