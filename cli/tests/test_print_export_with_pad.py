"""A `PRINT -f beancount` export of a ledger with a pad passes `bea check` (w5/085).

The export carried both the `pad` directive and the padding transaction
Beancount synthesized from it, so the reloaded file reported the pad unused.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

PADDED = """\
2024-01-01 open Assets:Cash USD
2024-01-01 open Equity:Open
2024-01-09 pad Assets:Cash Equity:Open
2024-01-10 balance Assets:Cash  42.00 USD
"""
PLAIN = """\
2024-01-01 open Assets:Cash USD
2024-01-01 open Equity:Open
2024-01-09 * "Seed"
  Assets:Cash  42.00 USD
  Equity:Open
2024-01-10 balance Assets:Cash  42.00 USD
"""


def _export(tmp_path: Path, text: str, query: str = "PRINT") -> str:
    ledger = tmp_path / "book.bean"
    ledger.write_text(text)
    out = tmp_path / "out.bean"
    result = runner.invoke(app, ["--file", str(ledger), "query", query, "-f", "beancount", "-o", str(out)])
    assert result.exit_code == 0, result.output
    return out.read_text()


def test_the_export_of_a_padded_ledger_reloads_cleanly(tmp_path: Path, bea_config_dir: Path) -> None:
    exported = _export(tmp_path, PADDED)

    assert exported.count(" pad ") == 1 and exported.count(" balance ") == 1
    assert "Padding inserted" not in exported
    check = runner.invoke(app, ["--file", str(tmp_path / "out.bean"), "check"])
    assert check.exit_code == 0, check.output
    total = runner.invoke(
        app, ["--file", str(tmp_path / "out.bean"), "query", "SELECT sum(position) AS t WHERE account = 'Assets:Cash'"]
    )
    assert "42.00 USD" in total.output


def test_a_padding_transaction_selected_without_its_pad_is_still_printed(tmp_path: Path, bea_config_dir: Path) -> None:
    exported = _export(tmp_path, PADDED, "PRINT FROM type = 'transaction'")

    assert "Padding inserted for Balance of 42.00 USD" in exported
    assert " pad " not in exported


def test_a_ledger_without_a_pad_exports_as_before(tmp_path: Path, bea_config_dir: Path) -> None:
    exported = _export(tmp_path, PLAIN)

    assert '2024-01-09 * "Seed"' in exported
    assert runner.invoke(app, ["--file", str(tmp_path / "out.bean"), "check"]).exit_code == 0
