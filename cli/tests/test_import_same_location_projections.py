"""Import compares real payments with declared transactions, not same-date plugin copies (w5/662)."""

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
OPENS = "2026-01-01 open Assets:Checking USD\n2026-01-01 open Expenses:Rent USD\n"
FEE_PLUGIN = """from decimal import Decimal
from beancount.core import data
__plugins__ = ["fees"]
def fees(entries, options_map):
    result = []
    for entry in entries:
        result.append(entry)
        if isinstance(entry, data.Transaction) and "inv" in entry.tags:
            result.append(data.Transaction(data.new_metadata(entry.meta["filename"], entry.meta["lineno"]),
                entry.date, "*", "Broker", "fee (generated)", frozenset(["gen"]), frozenset(), [
                    data.Posting("Expenses:Rent", data.Amount(Decimal(1), "USD"), None, None, None, None),
                    data.Posting("Assets:Checking", data.Amount(Decimal(-1), "USD"), None, None, None, None)]))
    return result, []
"""


def _import(root: Path, source: Path, *flags: str) -> dict[str, Any]:
    result = runner.invoke(
        app,
        [
            "--json", "--no-input", "--file", str(root), "import", str(source),
            "--csv", "date=Date,payee=Payee,narration=Narration,amount=Amount",
            "--account", "Assets:Checking", "--default-account", "Expenses:Rent", *flags,
        ],
    )  # fmt: skip
    assert result.exit_code == 0, result.output
    return dict(json.loads(result.stdout)["data"])


@pytest.mark.parametrize("payee", ["", '"Landlord" '])
@pytest.mark.parametrize("split", [False, True])
def test_the_first_forecast_projection_is_new_and_both_real_payments_are_written(
    tmp_path: Path, payee: str, split: bool
) -> None:
    root = tmp_path / "main.bean"
    template = (
        f'2026-01-15 # {payee}"Rent [MONTHLY REPEAT 3 TIMES]"\n  Expenses:Rent 1000 USD\n  Assets:Checking -1000 USD\n'
    )
    content = OPENS + 'plugin "fava.plugins.forecast"\n'
    if split:
        root.write_text(content + 'include "recurring.bean"\n')
        (tmp_path / "recurring.bean").write_text(template)
    else:
        root.write_text(content + template)
    source = tmp_path / "rent.csv"
    name = "Landlord" if payee else ""
    source.write_text(f"Date,Payee,Narration,Amount\n2026-01-15,{name},Rent,-1000\n2026-02-15,{name},Rent,-1000\n")
    before = {path: path.read_bytes() for path in tmp_path.glob("*.bean")}

    preview = _import(root, source)

    assert [row["status"] for row in preview["rows"]] == ["new", "new"]
    assert preview["possible_duplicates"] == 0
    assert {path: path.read_bytes() for path in tmp_path.glob("*.bean")} == before
    applied = _import(root, source, "--apply", "--duplicates", "skip")
    assert applied["written"] == 2
    assert all(row["match"] is None for row in applied["rows"])
    repeated = _import(root, source, "--apply", "--duplicates", "skip")
    assert repeated["written"] == 0 and repeated["duplicates"] == 2
    if split:
        assert (tmp_path / "recurring.bean").read_text() == template


@pytest.mark.parametrize("header", ['"buy" #inv', '"buy" #inv ; see "receipt"', '"Shop" "multi\nline" #inv'])
def test_a_generated_fee_at_a_written_transaction_location_never_hides_a_real_fee(tmp_path: Path, header: str) -> None:
    root = tmp_path / "main.bean"
    (tmp_path / "fees.py").write_text(FEE_PLUGIN)
    original = (
        'option "insert_pythonpath" "TRUE"\nplugin "fees"\n'
        + OPENS
        + f"2026-01-05 * {header}\n  Expenses:Rent 10 USD\n  Assets:Checking\n"
    )
    root.write_text(original)
    source = tmp_path / "fees.csv"
    source.write_text("Date,Payee,Narration,Amount\n2026-01-05,Broker,fee,-1.00\n")

    preview = _import(root, source)

    assert preview["rows"][0]["status"] == "new"
    assert preview["rows"][0]["match"] is None
    assert root.read_text() == original
    applied = _import(root, source, "--apply", "--duplicates", "skip")
    assert applied["written"] == 1
    repeated = _import(root, source)
    assert repeated["duplicates"] == 1


def test_an_ordinary_hash_flagged_written_transaction_is_still_a_duplicate(tmp_path: Path) -> None:
    root = tmp_path / "main.bean"
    original = OPENS + '2026-01-15 # "Rent"\n  Expenses:Rent 1000 USD\n  Assets:Checking\n'
    root.write_text(original)
    source = tmp_path / "paid.csv"
    source.write_text("Date,Payee,Narration,Amount\n2026-01-15,,Rent,-1000\n")

    result = _import(root, source, "--apply", "--duplicates", "skip")

    assert result["written"] == 0 and result["possible_duplicates"] == 1
    assert result["rows"][0]["match"]["filename"] == str(root)
    assert result["rows"][0]["match"]["lineno"] == 3
    assert root.read_text() == original


def test_forgetting_source_lines_also_refreshes_the_parsed_header(tmp_path: Path) -> None:
    from beancount.parser import parser

    from bea_engine.ledger.reader import entry_generated, forget_source_lines

    root = tmp_path / "main.bean"
    original = '2026-01-15 # "Old"\n  Expenses:Rent 1 USD\n  Assets:Checking\n'
    root.write_text(original)
    entries, _, _ = parser.parse_string(original.replace('"Old"', '"Changed"'))
    entry = entries[0]._replace(meta={"filename": str(root), "lineno": 1})
    forget_source_lines()
    assert entry_generated(entry, "transaction", require_declaration=True)

    root.write_text(original.replace('"Old"', '"Changed"'))
    forget_source_lines()

    assert not entry_generated(entry, "transaction", require_declaration=True)


def test_declaration_checks_parse_a_file_once_with_complete_headers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import unicodedata

    from beancount.parser import parser

    from bea_engine.ledger.reader import entry_generated, forget_source_lines

    root = tmp_path / "main.bean"
    content = (
        'option "name_expenses" "Aufwand"\n'
        '2026-01-15 * "Long\n' + "continued\n" * 210 + 'end"\n  Aufwand:Rent 1 USD\n  Assets:Checking\n'
        '2026-01-16 * "Shop" "Rent" ; see "receipt"\n  Aufwand:Rent 1 USD\n  Assets:Checking\n'
        '2026-01-17 * "Cafe\u0301" "Rent"\n  Aufwand:Rent 1 USD\n  Assets:Checking\n'
    )
    root.write_text(content)
    entries, errors, _ = parser.parse_string(content)
    assert not errors
    parse = parser.parse_string
    calls: list[int] = []

    def counted(*args: Any, **kwargs: Any) -> Any:
        calls.append(1)
        return parse(*args, **kwargs)

    monkeypatch.setattr(parser, "parse_string", counted)
    forget_source_lines()
    for original in entries:
        entry = original._replace(
            meta={**original.meta, "filename": str(root)},
            payee=unicodedata.normalize("NFC", original.payee) if original.payee else None,
        )
        assert not entry_generated(entry, "transaction", require_declaration=True)
    assert len(calls) == 1


def test_import_requires_a_readable_declaration_while_listing_keeps_its_location_policy(tmp_path: Path) -> None:
    from beancount.parser import parser

    from bea_engine.ledger.reader import entry_generated, forget_source_lines

    root = tmp_path / "main.bean"
    root.write_text('2026-01-15 * "unclosed\n')
    entries, _, _ = parser.parse_string('2026-01-15 * "Rent"\n  Expenses:Rent 1 USD\n  Assets:Checking\n')
    entry = entries[0]._replace(meta={"filename": str(root), "lineno": 1})
    forget_source_lines()

    assert not entry_generated(entry, "transaction")
    assert entry_generated(entry, "transaction", require_declaration=True)
