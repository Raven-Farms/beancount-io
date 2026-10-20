"""Four small gaps after w5/624, 627, 628 and 623 (w5/846).

Captured doctor runs and treeify named `bean-doctor`/`treeify` in usage
errors; `--csv auto` listed a QIF or OFX first line as "its columns"; every
query `InvalidOperation` was blamed on a NaN; and `cloud ledger list
--page/--limit` and `clone --dir` kept the last of repeated values.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
LEDGER = (
    "2026-01-01 open Assets:Savings USD\n2026-01-01 open Assets:Cash USD\n"
    '2026-01-02 * "x"\n  Assets:Cash  1 USD\n  Assets:Savings\n'
)
EXPORTS = {
    "qif": ("!Type:Bank\nD01/02/2026\nT-5.00\nPCoffee\n^\n", "a QIF"),
    "ofx": ("OFXHEADER:100\nDATA:OFXSGML\n", "an OFX"),
}


@pytest.mark.parametrize("csv", ["auto", "date=D,amount=T,narration=P"], ids=["auto", "mapping"])
@pytest.mark.parametrize("kind", sorted(EXPORTS))
def test_a_qif_or_ofx_export_under_csv_is_named_for_what_it_is(tmp_path: Path, kind: str, csv: str) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    text, name = EXPORTS[kind]
    export = tmp_path / f"bank.{kind}"
    export.write_text(text)

    result = runner.invoke(
        app, ["--no-input", "--file", str(ledger), "import", str(export), "--csv", csv, "--account", "Assets:Savings"]
    )

    assert result.exit_code == 2, result.output
    said = " ".join(result.stderr.split())
    assert f"bank.{kind} looks like {name} file, not a CSV export, so it has no columns to map" in said
    assert "Its columns are" not in said and "lacks" not in said
    assert ledger.read_text() == LEDGER


@pytest.mark.parametrize("query", ["SELECT round(number, 30) AS r", "SELECT decimal('1e30') % 7 AS r"])
def test_a_precision_failure_is_not_blamed_on_a_nan(tmp_path: Path, query: str) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)

    result = runner.invoke(app, ["--file", str(ledger), "query", query])

    assert result.exit_code == 1, result.output
    said = " ".join(result.stderr.split())
    assert "a result needs more than the 28 significant digits the arithmetic keeps" in said
    assert "NaN" not in said


@pytest.mark.parametrize(
    ("args", "said"),
    [
        (["cloud", "ledger", "list", "--page", "1", "--page", "3"], "--page '1' and --page '3'"),
        (["cloud", "ledger", "list", "--limit", "5", "--limit", "9"], "--limit '5' and --limit '9'"),
        (["cloud", "ledger", "clone", "me/x", "--dir", "a", "--dir", "b"], "--dir 'a' and --dir 'b'"),
    ],
    ids=["page", "limit", "clone-dir"],
)
def test_a_repeated_cloud_option_is_refused_before_any_request(args: list[str], said: str) -> None:
    result = runner.invoke(app, args)

    assert result.exit_code == 2, result.output
    assert f"Conflicting values for one option: {said}. Pass it once." in result.stderr


@pytest.mark.parametrize(
    ("args", "said"),
    [
        (["doctor", "roundtrip"], "Try 'bea doctor roundtrip --help' for help."),
        (["doctor", "directories"], "Try 'bea doctor directories --help' for help."),
        (["doctor", "linked", "{bom}"], "Try 'bea doctor linked --help' for help."),
        (["--file", "{ledger}", "treeify", "--nosuch"], "bea treeify: error: unrecognized arguments: --nosuch"),
    ],
    ids=["captured-doctor", "directories", "helper-doctor", "treeify"],
)
def test_usage_errors_name_the_bea_command(tmp_path: Path, args: list[str], said: str) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    bom = tmp_path / "bom.bean"
    bom.write_bytes(b"\xef\xbb\xbf" + LEDGER.encode())

    result = runner.invoke(app, [arg.format(ledger=ledger, bom=bom) for arg in args], input="")

    assert result.exit_code == 2, result.output
    assert said in result.output
    assert "bean-doctor" not in result.output and "usage: treeify" not in result.output
