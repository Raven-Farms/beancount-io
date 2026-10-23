"""A wide arithmetic `@@` total keeps every evaluated digit (w5/898).

The probe that reads the tail after `@@` used Beancount's raw parser under
its 28-digit context, so `(123456789012345.123456789012345+1)` was written
as `123456789012346.1234567890123`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_import_source_facts import _bea

LEDGER = "2024-01-01 open Assets:HOOL HOOL\n2024-01-01 open Assets:Cash USD\n"
EXACT = "123456789012346.123456789012345"
EXPRESSION = "(123456789012345.123456789012345+1)"


def _start(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)


@pytest.mark.parametrize(
    "total", [EXPRESSION, EXACT, "123,456,789,012,346.123456789012345"], ids=["sum", "plain", "grouped"]
)
def test_single_add_keeps_the_total(tmp_path: Path, total: str) -> None:
    _start(tmp_path)

    added = _bea(
        tmp_path, "add", "transaction", "QA total", "--date", "2024-02-01",
        "-p", f"Assets:HOOL 3 HOOL @@ {total} USD", "-p", "Assets:Cash",
    )  # fmt: skip

    assert added.returncode == 0, added.stderr
    assert f"@@ {EXACT} USD" in (tmp_path / "main.bean").read_text()
    assert json.loads(added.stdout)["data"]["directive"]["postings"][0]["price_total"]["number"] == EXACT
    assert _bea(tmp_path, "check").returncode == 0


def test_bulk_add_keeps_the_total(tmp_path: Path) -> None:
    _start(tmp_path)
    row = {
        "date": "2024-02-01",
        "narration": "QA total",
        "postings": [
            {"account": "Assets:HOOL", "amount": f"3 HOOL @@ {EXPRESSION} USD"},
            {"account": "Assets:Cash"},
        ],
    }
    (tmp_path / "input.json").write_text(json.dumps([row]))

    added = _bea(tmp_path, "add", "transactions", "--from", "input.json")

    assert added.returncode == 0, added.stderr
    assert f"@@ {EXACT} USD" in (tmp_path / "main.bean").read_text()


def test_a_small_sum_still_writes_its_value(tmp_path: Path) -> None:
    _start(tmp_path)

    added = _bea(
        tmp_path, "add", "transaction", "QA", "--date", "2024-02-01",
        "-p", "Assets:HOOL 3 HOOL @@ (40+60) USD", "-p", "Assets:Cash",
    )  # fmt: skip

    assert added.returncode == 0, added.stderr
    assert "@@ 100 USD" in (tmp_path / "main.bean").read_text()
