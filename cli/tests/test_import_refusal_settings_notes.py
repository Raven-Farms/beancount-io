"""Two import refusals carry the remembered-settings notes IMPORTING.md promises (w5/525).

The missing-account refusal (with an unreadable settings directory) and the
bad-date refusal (on a remembered run) raised before the notes were built,
so neither said the settings could not be read or which were in use.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Uncategorized USD
"""


@pytest.fixture
def books(tmp_path: Path) -> Iterator[Path]:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "aug.csv").write_text("Date,Description,Amount\n2026-08-01,COFFEE,-3.00\n")
    assert _import(tmp_path, "aug.csv", "--account", "Assets:Checking").returncode == 0
    try:
        yield tmp_path
    finally:
        (tmp_path / "config" / "importers").chmod(0o755)


def _import(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
        [sys.executable, "-m", "cli.main", "--json", "-f", str(tmp_path / "main.bean"), "import", *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _error(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    assert result.returncode == 2, result.stdout + result.stderr
    return dict(json.loads(result.stdout or result.stderr)["error"])


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads a mode-000 directory")
def test_the_missing_account_refusal_names_the_unreadable_settings(books: Path) -> None:
    (books / "config" / "importers").chmod(0)

    error = _error(_import(books, "aug.csv"))

    assert "not which account the export belongs to" in error["message"]
    assert any(detail.startswith("Cannot read remembered import settings in") for detail in error["details"])


def test_the_date_refusal_lists_the_remembered_settings_first(books: Path) -> None:
    (books / "aug2.csv").write_text("Date,Description,Amount\n2026-08-99,COFFEE,-3.00\n")

    error = _error(_import(books, "aug2.csv"))

    assert "cannot parse date '2026-08-99'" in error["message"]
    assert error["details"][0].startswith("Using settings remembered from aug.csv for aug2.csv:")
    assert "--account Assets:Checking" in error["details"][0]
