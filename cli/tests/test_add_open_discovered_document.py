"""An `add open` beaten by an auto-discovered file names the file (w5/765).

A file in the `option "documents"` folder dated before the proposed open
failed with `main.bean:0` and advice to edit a document directive that does
not exist. The refusal now names the discovered file and the option, and
offers moving the file or dating the open to it.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "documents" "docs"
option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Equity:Opening USD
"""


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
        COLUMNS="200",
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


def _books(tmp_path: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    (tmp_path / "docs" / "Assets" / "Cash").mkdir(parents=True)
    (tmp_path / "docs" / "Assets" / "Cash" / "2026-01-05.receipt.pdf").touch()
    (tmp_path / "docs" / "Assets" / "Card").mkdir(parents=True)
    (tmp_path / "docs" / "Assets" / "Card" / "2025-12-01.old.pdf").touch()
    return ledger


def test_late_open_names_the_discovered_file(tmp_path: Path) -> None:
    ledger = _books(tmp_path)
    before = ledger.read_bytes()
    result = _bea(tmp_path, "-f", str(ledger), "add", "open", "--date", "2026-01-01", "--account", "Assets:Card")
    assert result.returncode == 1, result.stdout
    pdf = str(tmp_path / "docs" / "Assets" / "Card" / "2025-12-01.old.pdf")
    assert pdf in result.stderr, result.stderr
    assert 'option "documents" "docs"' in result.stderr
    assert "date it on or before 2025-12-01" in result.stderr
    assert "Move the file out of the documents folder or correct the proposed open date" in result.stderr
    assert "Correct the document date" not in result.stderr
    assert ledger.read_bytes() == before


def test_open_on_the_file_date_writes(tmp_path: Path) -> None:
    ledger = _books(tmp_path)
    result = _bea(tmp_path, "-f", str(ledger), "add", "open", "--date", "2025-12-01", "--account", "Assets:Card")
    assert result.returncode == 0, result.stderr
    assert "2025-12-01 open Assets:Card" in ledger.read_text()
