"""An importer's balance or note on a never-opened account is blocked, like a transaction (w5/351).

Only transactions went through the open check, so a statement's closing
`balance` on a new account was counted ready and `--apply` then failed the
whole batch with exit 1.
"""

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
2026-01-01 open Assets:Bank
2026-01-01 open Equity:Opening
2026-01-02 * "Seed"
  Assets:Bank  100 USD
  Equity:Opening
"""
IMPORTER = """\
import datetime
from decimal import Decimal as D
from beancount.core import amount, data


class Statement:
    name = "statement"

    def identify(self, filepath):
        return filepath.endswith(".txt")

    def account(self, filepath):
        return "Assets:Bank"

    def extract(self, filepath, existing):
        kind = open(filepath).read().strip()
        meta = data.new_metadata("x", 1)
        day = datetime.date(2026, 1, 10)
        out = []
        if kind == "with-open":
            out.append(data.Open(meta, datetime.date(2026, 1, 1), "Assets:Nope", ["USD"], None))
        if kind in ("balance", "with-open"):
            out.append(data.Balance(meta, day, "Assets:Nope", amount.Amount(D("0"), "USD"), None, None))
        if kind == "note":
            out.append(data.Note(meta, day, "Assets:Nope", "hello", None, None))
        return out


CONFIG = [Statement()]
"""


def _import(tmp_path: Path, kind: str, *flags: str) -> tuple[int, Any]:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "imp.py").write_text(IMPORTER)
    (tmp_path / "s.txt").write_text(kind)
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
        [
            sys.executable,
            "-m",
            "cli.main",
            "--json",
            "--no-input",
            "-f",
            "main.bean",
            "import",
            "s.txt",
            "--config",
            "imp.py",
            *flags,
        ],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )
    payload = json.loads(result.stdout or result.stderr)
    return result.returncode, payload.get("data", payload.get("error"))


@pytest.mark.parametrize("kind", ["balance", "note"])
def test_the_directive_is_blocked_and_apply_exits_4(tmp_path: Path, kind: str) -> None:
    code, data = _import(tmp_path, kind)
    assert code == 0
    (row,) = data["rows"]
    assert data["ready"] == 0 and row["status"] == "blocked"
    assert row["accounts"] == ["Assets:Nope"]
    assert "bea add open --account Assets:Nope" in row["reason"]

    code, _ = _import(tmp_path, kind, "--apply")
    assert code == 4
    assert (tmp_path / "main.bean").read_text() == LEDGER


def test_an_open_in_the_same_batch_unblocks_it(tmp_path: Path) -> None:
    code, data = _import(tmp_path, "with-open")
    assert code == 0
    assert data["ready"] == 2 and data["blocked"] == 0
