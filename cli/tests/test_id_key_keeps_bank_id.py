"""`--id-key` must not turn off the bank ids a `--csv id=` mapping writes (w5/254)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2020-01-01 open Assets:Bank:Checking USD
2020-01-01 open Expenses:Uncategorized
2020-01-01 open Equity:Opening-Balances

2020-01-01 * "seed"
  Assets:Bank:Checking      100 USD
  Equity:Opening-Balances  -100 USD
"""
FIRST = "Date,Description,Amount,ID\n2024-03-10,Cafe,-4.50,id1\n"
REUSED = "Date,Description,Amount,ID\n2024-03-11,Other,-9.99,id1\n"


def _import(tmp_path: Path, source: str, mapping: str, id_key: str) -> subprocess.CompletedProcess[str]:
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
        [
            sys.executable,
            "-m",
            "cli.main",
            "--no-input",
            "-f",
            "main.bean",
            "import",
            source,
            "--csv",
            mapping,
            "--account",
            "Assets:Bank:Checking",
            "--id-key",
            id_key,
            "--apply",
        ],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
    )


def _books(tmp_path: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    (tmp_path / "a.csv").write_text(FIRST)
    (tmp_path / "b.csv").write_text(REUSED)
    return ledger


# `id` is the lowercase control; `ID` is the header spelling; `other` names a
# key the mapping never writes.
@pytest.mark.parametrize("id_key", ["id", "ID", "Id", "other"])
def test_reused_bank_id_is_a_conflict_whatever_id_key_says(tmp_path: Path, id_key: str) -> None:
    ledger = _books(tmp_path)
    mapping = "date=Date,amount=Amount,narration=Description,id=ID"

    first = _import(tmp_path, "a.csv", mapping, id_key)
    assert first.returncode == 0, first.stderr
    written = ledger.read_text()
    assert 'import-id: "bank:id1"' in written

    second = _import(tmp_path, "b.csv", mapping, id_key)
    assert second.returncode == 4, (second.returncode, second.stdout, second.stderr)
    assert "Stable ID matches an entry with different transaction data." in second.stdout + second.stderr
    assert ledger.read_text() == written


def test_mapping_without_id_still_imports_by_content(tmp_path: Path) -> None:
    ledger = _books(tmp_path)
    mapping = "date=Date,amount=Amount,narration=Description"

    for source in ("a.csv", "b.csv"):
        result = _import(tmp_path, source, mapping, "ID")
        assert result.returncode == 0, result.stderr
    text = ledger.read_text()
    assert text.count('import-id: "csv:sha256:') == 2
    assert "bank_id" not in text
