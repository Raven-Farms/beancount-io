"""The inactive-account remedy names the directive being added, not always "transaction" (w5/393)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD
"""
EARLY = "2025-12-01"


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
        [sys.executable, "-m", "cli.main", *args],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize(
    ("noun", "args"),
    [
        ("note", ("note", "--date", EARLY, "-a", "Assets:Cash", "-m", "early")),
        ("transaction", ("transaction", "X", "--date", EARLY, "-p", "Expenses:Food 5 USD", "-p", "Assets:Cash")),
    ],
)
def test_remedy_names_the_directive(tmp_path: Path, noun: str, args: tuple[str, ...]) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    result = _bea(tmp_path, "-f", str(ledger), "add", *args)

    assert result.returncode == 1, result.stderr
    assert ledger.read_text() == LEDGER
    flat = " ".join(result.stderr.split())
    assert f"Account opened 2026-01-01 at {ledger}:2. Correct the {noun} date or edit that directive;" in flat


def test_json_document_refusal_names_the_document(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "r.pdf").write_bytes(b"%PDF-1.4\n")
    result = _bea(
        tmp_path,
        "--json",
        "-f",
        str(ledger),
        "add",
        "document",
        "--date",
        EARLY,
        "-a",
        "Assets:Cash",
        "--filename",
        "docs/r.pdf",
    )

    assert result.returncode == 1, result.stderr
    flat = json.dumps(json.loads(result.stdout or result.stderr))
    assert "Correct the document date or edit that directive;" in flat
    assert "Correct the transaction date" not in flat
