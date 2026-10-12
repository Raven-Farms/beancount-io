"""`bea check` keeps the verdict bean-check reached under its own options (w5/088).

After bean-check accepted the ledger, a second load — added for the
out-of-tree document rule — re-validated it without those options, so
`check --auto` failed a ledger `bean-check --auto` accepts and
`check --version` went on to report ledger errors.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

NO_OPENS = '2026-01-02 * "no opens"\n  Assets:Cash  -5 USD\n  Expenses:Food  5 USD\n'
OPENED = "2026-01-01 open Assets:Cash\n2026-01-01 open Expenses:Food\n" + NO_OPENS


def _check(ledger: Path, *args: str) -> Any:
    return runner.invoke(app, ["--file", str(ledger), "check", *args])


@pytest.mark.parametrize("flag", ["--auto", "-a"])
def test_auto_accepts_a_ledger_without_open_directives(tmp_path: Path, bea_config_dir: Path, flag: str) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(NO_OPENS)

    result = _check(ledger, flag)

    assert result.exit_code == 0, result.output
    assert "unknown account" not in result.output


def test_without_auto_the_same_ledger_still_fails(tmp_path: Path, bea_config_dir: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(NO_OPENS)

    assert _check(ledger).exit_code == 1


def test_auto_still_reports_a_real_error(tmp_path: Path, bea_config_dir: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(NO_OPENS.replace("  Expenses:Food  5 USD", "  Expenses:Food  6 USD"))

    result = _check(ledger, "--auto")

    assert result.exit_code == 1, result.output
    assert "does not balance" in result.output


def test_version_prints_the_version_and_reads_no_ledger(tmp_path: Path, bea_config_dir: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(NO_OPENS)

    result = _check(ledger, "--version")

    assert result.exit_code == 0, result.output
    assert result.output.strip().startswith("Beancount ")
    assert len(result.output.strip().splitlines()) == 1


@pytest.mark.parametrize("flags", [[], ["--auto"], ["-v"]], ids=["plain", "auto", "verbose"])
def test_a_document_outside_the_ledger_tree_still_fails(tmp_path: Path, bea_config_dir: Path, flags: list[str]) -> None:
    elsewhere = tmp_path / "elsewhere"
    books = tmp_path / "books"
    elsewhere.mkdir()
    books.mkdir()
    (elsewhere / "invoice.pdf").write_bytes(b"%PDF-1.4 fake")
    ledger = books / "main.bean"
    ledger.write_text(OPENED + f'2026-01-03 document Expenses:Food "{elsewhere / "invoice.pdf"}"\n')

    result = _check(ledger, *flags)

    assert result.exit_code == 1, result.output
    assert "outside the ledger" in " ".join(result.output.split())
