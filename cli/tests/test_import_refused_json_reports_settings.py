"""A refused `--json` import reports the settings it resolved, as its preview does (w5/282).

The frontend's settings notes go to stderr, which JSON mode does not print, and
`remembered` and `date_format` were added to the envelope only on success. A
flag-free `--apply` refused for review therefore told an agent that a
remembered mapping was used, but not which one or how its dates were read.
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

LEDGER = (
    'option "operating_currency" "USD"\n'
    "2026-01-01 open Assets:Checking USD\n"
    "2026-01-01 open Assets:Savings USD\n"
    "2026-01-01 open Expenses:Food\n"
    "2026-01-01 open Expenses:Uncategorized\n"
)
HEADER = "Date,Description,Amount,FITID\n"
EXPLICIT = (
    "--csv",
    "date=Date,amount=Amount,narration=Description,id=FITID",
    "--account",
    "Assets:Checking",
    "--rules",
    "rules.toml",
    "--default-account",
    "Expenses:Food",
)
AMBIGUOUS = "Dates parse as %m/%d/%Y but the column has no day past the twelfth"


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--file", "main.bean", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.fixture
def book(tmp_path: Path) -> Path:
    """A ledger holding one imported row, whose mapping is remembered for the header."""
    (tmp_path / "main.bean").write_text(LEDGER, encoding="utf-8")
    (tmp_path / "rules.toml").write_text('[[rule]]\nmatch = "grocer"\naccount = "Expenses:Food"\n', encoding="utf-8")
    (tmp_path / "dup1.csv").write_text(HEADER + "2026-04-02,Grocer,-20.00,A1\n", encoding="utf-8")
    # Same day, text and amount under another bank ID: a possible duplicate.
    (tmp_path / "dup2.csv").write_text(HEADER + "04/02/2026,Grocer,-20.00,B7\n", encoding="utf-8")
    seeded = _bea(tmp_path, "import", "dup1.csv", *EXPLICIT, "--apply")
    assert seeded.returncode == 0, seeded.stderr
    return tmp_path


def _preview(book: Path, *args: str) -> Any:
    done = _bea(book, "--json", "import", "dup2.csv", *args)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)["data"]


def _refused(book: Path, *args: str) -> Any:
    done = _bea(book, "--json", "import", "dup2.csv", *args, "--apply")
    assert done.returncode == 4, done.stderr
    assert done.stdout == ""
    return json.loads(done.stderr)["error"]


def test_refused_recalled_apply_reports_what_the_preview_does(book: Path) -> None:
    preview = _preview(book)
    error = _refused(book)

    # Control: the preview of the same command already carried all three.
    assert preview["remembered"]["mapping"] == "date=Date,amount=Amount,narration=Description,id=FITID"
    assert preview["remembered"]["default_account"] == "Expenses:Food"
    assert preview["date_format"] == "%m/%d/%Y"
    assert len(preview["notes"]) == 2
    assert preview["notes"][0].startswith("Using settings remembered from dup1.csv for dup2.csv: --csv ")
    assert preview["notes"][1].startswith(AMBIGUOUS)

    result = error["result"]
    assert result["config_source"] == "remembered --csv"
    assert result["written"] == 0
    assert result["remembered"] == preview["remembered"]
    assert result["date_format"] == preview["date_format"]
    assert result["notes"] == preview["notes"]
    # The review rows stay the error's own details; the notes are not repeated there.
    assert len(error["details"]) == 1 and error["details"][0].startswith("Row 1 (possible_duplicate)")


def test_refused_explicit_apply_reports_its_notes_and_no_memory(book: Path) -> None:
    preview = _preview(book, *EXPLICIT)
    error = _refused(book, *EXPLICIT)

    assert preview["remembered"] is None
    assert preview["notes"][0] == "Using column mapping (--csv)."
    result = error["result"]
    assert "remembered" in result and result["remembered"] is None
    assert result["date_format"] == preview["date_format"] == "%m/%d/%Y"
    assert result["notes"] == preview["notes"]


def test_failure_without_a_preview_lists_the_settings_in_details(book: Path) -> None:
    done = _bea(book, "--json", "import", "dup2.csv", "--into", "absent/2026.bean", "--apply")

    assert done.returncode == 2, done.stderr
    error = json.loads(done.stderr)["error"]
    assert "does not exist" in error["message"]
    assert "result" not in error
    assert error["details"][0].startswith("Using settings remembered from dup1.csv for dup2.csv: --csv ")
    assert error["details"][1].startswith(AMBIGUOUS)


def test_failure_without_a_preview_keeps_typed_settings_out_of_details(book: Path) -> None:
    done = _bea(book, "--json", "import", "dup2.csv", *EXPLICIT, "--into", "absent/2026.bean", "--apply")

    assert done.returncode == 2, done.stderr
    error = json.loads(done.stderr)["error"]
    assert "does not exist" in error["message"]
    # Nothing was recalled or inferred, so the error's details stay its own.
    assert not any("Using column mapping" in line for line in error.get("details", []))


def test_human_refusal_prints_each_note_once(book: Path) -> None:
    done = _bea(book, "import", "dup2.csv", "--apply")

    assert done.returncode == 4, done.stderr
    assert done.stderr.count("Using settings remembered from dup1.csv for dup2.csv") == 1
    assert done.stderr.count(AMBIGUOUS) == 1
    assert "Error: Import needs review; nothing was written." in done.stderr
