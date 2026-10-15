"""An atomic bulk refusal names the rows that fail ledger validation (w5/337).

It counted the good rows ("Pass --partial to append the 49 valid rows") but
printed Beancount's message without a row number and listed every row as
`unwritten_rows`, so the user had to bisect, or write data with `--partial`.
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
LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Expenses:Food USD\n2026-01-01 open Assets:Cash USD\n'
BAD = {
    "unbalanced": [{"account": "Expenses:Food", "amount": "5 USD"}, {"account": "Assets:Cash", "amount": "-4 USD"}],
    "unknown-account": [{"account": "Expenses:Nope", "amount": "1 USD"}, {"account": "Assets:Cash"}],
}


def _rows(bad: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for n in range(12):
        postings = bad if n == 7 else [{"account": "Expenses:Food", "amount": "1.25 USD"}, {"account": "Assets:Cash"}]
        rows.append({"date": f"2026-02-{n + 1:02d}", "narration": f"r{n}", "postings": postings})
    return rows


def _add(tmp_path: Path, *flags: str) -> subprocess.CompletedProcess[str]:
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
        [sys.executable, "-m", "cli.main", *flags, "-f", "main.bean", "add", "transactions", "--from", "in.json"],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize("case", sorted(BAD))
def test_the_refusal_names_the_failing_row(tmp_path: Path, case: str) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "in.json").write_text(json.dumps(_rows(BAD[case])))

    text = _add(tmp_path)
    assert text.returncode == 1
    assert "Pass --partial to append the 11 valid rows." in " ".join(text.stderr.split())
    assert "Row 8: " in text.stderr

    as_json = _add(tmp_path, "--json")
    error = json.loads(as_json.stdout or as_json.stderr)["error"]
    assert error["result"]["rejected_rows"] == [7]
    assert len(error["result"]["unwritten_rows"]) == 12
    assert all(detail.startswith("Row 8: ") for detail in error["details"])
    assert (tmp_path / "main.bean").read_text() == LEDGER
