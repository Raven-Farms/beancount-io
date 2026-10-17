"""A write through an included file is reported, and remembered, as the root's (w5/613).

Since w5/343, a write with `--file` on an included leaf runs through its
root, but only the engine knew. `target.file` named the leaf while the same
write with `--file main.bean --into txns.bean` named the root. The redirect
note reached stderr but never `--json`, and import memory was kept under the
leaf, invisible to the root, and the other way round.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
MAIN = (
    'option "operating_currency" "USD"\n'
    "2026-01-01 open Assets:Cash USD\n"
    "2026-01-01 open Expenses:Food\n"
    "2026-01-01 open Expenses:Uncategorized\n"
    'include "txns.bean"\n'
)
MAPPING = "date=Date,narration=Description,amount=Amount"


@pytest.fixture
def books(tmp_path: Path, bea_config_dir: Path) -> Path:
    (tmp_path / "main.bean").write_text(MAIN)
    (tmp_path / "txns.bean").write_text('2026-01-02 * "a"\n  Expenses:Food  1 USD\n  Assets:Cash\n')
    (tmp_path / "x.csv").write_text("Date,Description,Amount\n2026-02-01,Lunch,-9.00\n")
    (tmp_path / "y.csv").write_text("Date,Description,Amount\n2026-02-02,Dinner,-12.00\n")
    return tmp_path


def _bea(books: Path, ledger: str, *args: str) -> dict[str, Any]:
    result = runner.invoke(app, ["--json", "--no-input", "--file", str(books / ledger), *args])
    assert result.exit_code == 0, result.output
    payload: dict[str, Any] = json.loads(result.stdout)
    return payload


def _redirect(books: Path) -> str:
    root = books / "main.bean"
    return f"txns.bean is included by {root}; the write goes to txns.bean and is checked against that whole ledger."


def test_an_add_through_the_leaf_reports_the_root_and_the_note(books: Path) -> None:
    posting = ["-p", "Expenses:Food 2 USD", "-p", "Assets:Cash"]
    leaf = _bea(books, "txns.bean", "add", "transaction", "--date", "2026-01-03", "b", *posting)
    root = _bea(books, "main.bean", "add", "transaction", "--into", "txns.bean", "--date", "2026-01-04", "c", *posting)

    assert leaf["target"] == root["target"] == {"file": str(books / "main.bean"), "into": str(books / "txns.bean")}
    assert leaf["data"]["warnings"] == [_redirect(books)]
    assert "root" not in leaf["data"]


def test_an_import_through_the_leaf_is_remembered_for_the_root(books: Path, bea_config_dir: Path) -> None:
    leaf = _bea(
        books, "txns.bean", "import", str(books / "x.csv"), "--csv", MAPPING, "--account", "Assets:Cash", "--apply"
    )

    assert leaf["target"]["file"] == str(books / "main.bean")
    assert leaf["data"]["notes"][0] == _redirect(books)

    root = _bea(books, "main.bean", "import", str(books / "y.csv"), "--into", "txns.bean")
    assert root["data"]["config_source"] == "remembered --csv"
    assert root["data"]["ready"] == 1
    assert len(list((bea_config_dir / "importers").glob("csv-*.json"))) == 1


def test_a_mapping_remembered_at_the_root_serves_the_leaf(books: Path) -> None:
    _bea(
        books,
        "main.bean",
        "import",
        str(books / "x.csv"),
        "--csv",
        MAPPING,
        "--account",
        "Assets:Cash",
        "--into",
        "txns.bean",
    )

    leaf = _bea(books, "txns.bean", "import", str(books / "y.csv"))

    assert leaf["data"]["config_source"] == "remembered --csv"
    assert leaf["target"]["file"] == str(books / "main.bean")
