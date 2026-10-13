"""A lone surrogate escape in a bulk row rejects that row, not the batch (w5/185).

JSON can spell half a surrogate pair (`\\ud83d`, an emoji cut in two) and the
parser keeps it, but no UTF-8 file can hold one. It used to reach the first
encode of the staged batch: a raw `UnicodeEncodeError` naming no row, with
nothing written even under `--partial`.
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
LEDGER = "2026-01-01 open Assets:Cash USD\n2026-01-01 open Expenses:Food\n"
HIGH = "\ud83d"
LOW = "\udc00"


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _row(n: int, **fields: Any) -> dict[str, Any]:
    return {
        "date": f"2026-02-0{n}",
        "narration": f"r{n}",
        "postings": [{"account": "Expenses:Food", "amount": f"1{n - 1} USD"}, {"account": "Assets:Cash"}],
        **fields,
    }


def _run(tmp_path: Path, second: dict[str, Any], *extra: str) -> tuple[subprocess.CompletedProcess[str], Path]:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    rows = tmp_path / "rows.json"
    # ensure_ascii spells the lone surrogate as the `\udXXX` escape other tools emit.
    rows.write_text(json.dumps([_row(1), second, _row(3)]), encoding="ascii")
    leading = [flag for flag in extra if flag == "--json"]
    trailing = [flag for flag in extra if flag != "--json"]
    args = (*leading, "--file", str(ledger), "add", "transactions", "--from", str(rows), *trailing)
    return _bea(tmp_path, *args), ledger


def _posting_row(**posting: Any) -> dict[str, Any]:
    food = {"account": "Expenses:Food", "amount": "11 USD", **posting}
    return _row(2, postings=[food, {"account": "Assets:Cash"}])


CASES = [
    pytest.param(_row(2, narration=f"Coffee {HIGH}"), "narration", "\\ud83d", id="narration"),
    pytest.param(_row(2, narration=f"Coffee {LOW}"), "narration", "\\udc00", id="low-surrogate"),
    pytest.param(_row(2, payee=f"Shop {HIGH}"), "payee", "\\ud83d", id="payee"),
    pytest.param(_row(2, meta={"note": f"x {HIGH}"}), "meta.note", "\\ud83d", id="meta-value"),
    pytest.param(_posting_row(account=f"Expenses:Food{HIGH}"), "postings.0.account", "\\ud83d", id="account"),
    pytest.param(_posting_row(meta={"memo": f"x {HIGH}"}), "postings.0.meta.memo", "\\ud83d", id="posting-meta"),
]


@pytest.mark.parametrize(("second", "field", "escape"), CASES)
def test_partial_rejects_only_the_surrogate_row(
    tmp_path: Path, second: dict[str, Any], field: str, escape: str
) -> None:
    result, ledger = _run(tmp_path, second, "--json", "--partial")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "UnicodeEncodeError" not in result.stdout + result.stderr
    error = json.loads(result.stderr)["error"]
    assert error["result"] == {"written": 2, "written_rows": [0, 2], "rejected_rows": [1]}
    detail = error["details"][0]
    assert detail.startswith(f"Row 2, {field}: "), detail
    assert escape in detail and "unpaired surrogate" in detail
    text = ledger.read_text()
    assert '"r1"' in text and '"r3"' in text
    assert "2026-02-02" not in text


def test_without_partial_names_the_row_and_writes_nothing(tmp_path: Path) -> None:
    result, ledger = _run(tmp_path, _row(2, narration=f"Coffee {HIGH}"))
    assert result.returncode == 1, result.stdout + result.stderr
    assert "UnicodeEncodeError" not in result.stderr
    assert "Row 2, narration: " in result.stderr
    assert "\\ud83d" in result.stderr
    assert ledger.read_text() == LEDGER


def test_surrogate_in_a_key_is_named_without_printing_it(tmp_path: Path) -> None:
    result, ledger = _run(tmp_path, _row(2, meta={f"no{HIGH}te": "x"}), "--partial")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "Row 2, meta.no\\ud83dte (key): " in result.stderr
    assert ledger.read_text().count(" * ") == 2


@pytest.mark.parametrize(
    "narration",
    [pytest.param("Coffee \x1b", id="control-character"), pytest.param("Coffee \U0001f600", id="paired-surrogates")],
)
def test_other_escapes_still_write_every_row(tmp_path: Path, narration: str) -> None:
    result, ledger = _run(tmp_path, _row(2, narration=narration), "--json", "--partial")
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["data"]["written"] == 3
    assert ledger.read_text(encoding="utf-8").count(" * ") == 3
