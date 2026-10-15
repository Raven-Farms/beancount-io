"""`import --date-format ''` is refused and never remembered (w5/385).

An empty value was read as "not given": the import ran, but `""` was saved
as the file's date format, and every later plain `bea import s.csv` failed
with "Remembered --date-format '' does not match". A memory file that already
holds `""` now reads as unset.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = (
    'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n2026-01-01 open Expenses:Uncategorized USD\n'
)
CSV = "Date,Payee,Narration,Amount\n2026-01-07,Shop,stuff,-3.00\n"
MAPPING = "date=Date,payee=Payee,narration=Narration,amount=Amount"


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
        [sys.executable, "-m", "cli.main", "-f", "main.bean", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "s.csv").write_text(CSV)
    return tmp_path


def _memory(books: Path) -> list[Path]:
    return sorted((books / "config" / "importers").glob("*.json")) if (books / "config" / "importers").is_dir() else []


@pytest.mark.parametrize("value", ["", " "])
def test_an_empty_date_format_is_refused_and_nothing_is_saved(books: Path, value: str) -> None:
    result = _bea(books, "import", "s.csv", "--csv", MAPPING, "--account", "Assets:Cash", "--date-format", value)

    assert result.returncode == 2, result.stdout + result.stderr
    assert f"--date-format {value!r} is empty" in result.stderr
    assert not any('"date_format": ""' in path.read_text() for path in _memory(books))


def test_a_remembered_empty_date_format_no_longer_blocks_a_plain_import(books: Path) -> None:
    first = _bea(books, "import", "s.csv", "--csv", MAPPING, "--account", "Assets:Cash")
    assert first.returncode == 0, first.stderr
    [memory] = _memory(books)
    record = json.loads(memory.read_text())
    [entry] = record["sources"]
    entry["date_format"] = ""  # what a run before w5/385 saved
    memory.write_text(json.dumps(record))

    again = _bea(books, "import", "s.csv")

    assert again.returncode == 0, again.stderr
    assert "Remembered --date-format" not in again.stderr
