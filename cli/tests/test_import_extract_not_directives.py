"""An importer whose `extract()` returns something other than directives is named (w5/319).

A returned string was split into characters and failed as `'str' object has
no attribute '_replace'`; a dict or `None` row failed the same way, and a
returned `None` as "not iterable" — none of them saying what was wrong.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Bank USD
2026-01-01 open Expenses:Food USD
"""
IMPORTER = """\
import datetime
from decimal import Decimal as D
from beancount.core import amount, data


def valid():
    postings = [
        data.Posting("Assets:Bank", amount.Amount(D("-1"), "USD"), None, None, None, None),
        data.Posting("Expenses:Food", amount.Amount(D("1"), "USD"), None, None, None, None),
    ]
    meta = data.new_metadata("stmt.txt", 1)
    return data.Transaction(meta, datetime.date(2026, 1, 5), "*", None, "x", frozenset(), frozenset(), postings)


class Imp:
    name = "imp"

    def identify(self, filepath):
        return filepath.endswith("stmt.txt")

    def account(self, filepath):
        return "Assets:Bank"

    def extract(self, filepath, existing):
        return {result}


CONFIG = [Imp()]
"""


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        ('"abc"', "extract() returned a str instead of a list of Beancount directives"),
        ('[{"date": "2026-01-05"}]', "row 1 is a dict, not a Beancount directive"),
        ("[valid(), None]", "row 2 is None, not a Beancount directive"),
        ("None", "extract() returned None instead of a list of Beancount directives"),
    ],
    ids=["string", "dict-row", "none-row", "none"],
)
def test_a_non_directive_is_named(tmp_path: Path, result: str, expected: str) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "stmt.txt").write_text("x\n")
    (tmp_path / "imp.py").write_text(IMPORTER.format(result=result))
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    run = subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", "-f", "main.bean", "import", "stmt.txt", "--config", "imp.py"],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )
    message = " ".join(run.stderr.split())
    assert run.returncode == 1, run.stderr
    assert expected in message and "Importer imp" in message
    assert "_replace" not in message and "not iterable" not in message
    assert (tmp_path / "main.bean").read_text() == LEDGER
