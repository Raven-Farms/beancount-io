"""Import NFC-normalizes importer accounts and CSV category cells (w5/530).

An importer's NFD `Expenses:Café` was "not open", with a duplicate `add open`
as the remedy, and an NFD category cell was "not an account name" and went
to Uncategorized, though both are the open `Expenses:Café`.
"""

from __future__ import annotations

import os
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = (
    'option "operating_currency" "EUR"\n2026-01-01 open Assets:Checking EUR\n'
    "2026-01-01 open Expenses:Café\n2026-01-01 open Expenses:Uncategorized\n"
)
NFD = unicodedata.normalize("NFD", "Expenses:Café")
IMPORTER = f"""import datetime
from decimal import Decimal
from beancount.core import amount, data


class Stmt:
    name = "stmt"

    def identify(self, filepath):
        return filepath.endswith(".txt")

    def account(self, filepath):
        return {unicodedata.normalize("NFD", "Assets:Checking")!r}

    def extract(self, filepath, existing):
        meta = data.new_metadata(filepath, 1)
        legs = [
            data.Posting("Assets:Checking", amount.Amount(Decimal("-4.50"), "EUR"), None, None, None, None),
            data.Posting({NFD!r}, amount.Amount(Decimal("4.50"), "EUR"), None, None, None, None),
        ]
        return [data.Transaction(meta, datetime.date(2026, 3, 1), "*", None, "Coffee", frozenset(), frozenset(), legs)]


CONFIG = [Stmt()]
"""


def _import(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), "import", *args, "--apply"],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _written(tmp_path: Path) -> str:
    return (tmp_path / "main.bean").read_text()[len(LEDGER) :]


def test_an_importer_nfd_account_resolves(tmp_path: Path) -> None:
    (tmp_path / "importers.py").write_text(IMPORTER)
    (tmp_path / "stmt.txt").write_text("x\n")

    result = _import(tmp_path, "stmt.txt", "--config", "importers.py")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "is not open" not in result.stdout + result.stderr
    written = _written(tmp_path)
    assert "Expenses:Café" in written and NFD not in written


@pytest.mark.parametrize("cell", [NFD])
def test_an_nfd_category_cell_resolves(tmp_path: Path, cell: str) -> None:
    (tmp_path / "bank.csv").write_text(f"Date,Description,Amount,Category\n2026-03-01,Coffee,-4.50,{cell}\n")

    result = _import(
        tmp_path,
        "bank.csv",
        "--account",
        "Assets:Checking",
        "--csv",
        "date=Date,amount=Amount,narration=Description,category=Category",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "not an account name" not in result.stdout + result.stderr
    written = _written(tmp_path)
    assert written.lstrip().startswith('2026-03-01 * "Coffee"')
    assert "Expenses:Café" in written and "Uncategorized" not in written
