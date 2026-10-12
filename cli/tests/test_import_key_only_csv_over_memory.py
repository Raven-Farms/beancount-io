"""A `--csv` that carries only keys applies them on top of the remembered mapping (w5/078).

After a ledger-signed import, the next file is read bank-signed and bea
advises `--csv sign=ledger`. That exact command ignored the remembered
mapping, re-inferred from the header, and failed — or replaced the saved
settings with an inferred mapping.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

LEDGER = (
    'option "operating_currency" "USD"\n'
    "2026-01-01 open Liabilities:Card USD\n"
    "2026-01-01 open Expenses:Food\n"
    "2026-01-01 open Expenses:Uncategorized\n"
)
GERMAN = "date=Datum,narration=Text,amount=Betrag"


@pytest.fixture
def book(tmp_path: Path, bea_config_dir: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    return ledger


def _import(book: Path, name: str, content: str | bytes, *args: str) -> Any:
    source = book.parent / name
    source.write_bytes(content if isinstance(content, bytes) else content.encode())
    return runner.invoke(app, ["--json", "--no-input", "--file", str(book), "import", str(source), *args])


def _data(result: Any) -> Any:
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)["data"]


def _record(config: Path) -> Any:
    (record,) = (config / "importers").glob("csv-*.json")
    return json.loads(record.read_text())["sources"]


def test_the_advised_sign_key_applies_over_the_remembered_mapping(book: Path, bea_config_dir: Path) -> None:
    first = _data(
        _import(
            book,
            "a.csv",
            "Datum,Text,Betrag\n2026-01-05,Kaffee,3.00\n",
            "--account",
            "Liabilities:Card",
            "--csv",
            f"{GERMAN},sign=ledger",
            "--apply",
        )
    )
    next_file = "Datum,Text,Betrag\n2026-02-05,Tee,2.00\n"
    bank_signed = _data(_import(book, "b.csv", next_file))
    assert any("Pass --csv sign=ledger" in note for note in bank_signed["notes"])

    advised = _data(_import(book, "b.csv", next_file, "--csv", "sign=ledger"))
    applied = _data(_import(book, "b.csv", next_file, "--apply"))

    assert advised["config_source"] == "remembered --csv"
    assert advised["account"] == "Liabilities:Card"
    assert advised["rows"][0]["date"] == "2026-02-05"
    assert advised["rows"][0]["amount"] == first["rows"][0]["amount"].replace("3.00", "2.00")
    assert advised["rows"][0]["amount"] != bank_signed["rows"][0]["amount"]
    (stored,) = _record(bea_config_dir)
    assert stored["mapping"] == GERMAN and stored["account"] == "Liabilities:Card"
    assert applied["rows"][0]["amount"] == advised["rows"][0]["amount"]
    assert applied["written"] == 1


def test_a_sign_key_keeps_a_remembered_payee_mapping_and_its_rules(book: Path, bea_config_dir: Path) -> None:
    rules = book.parent / "rules.toml"
    rules.write_text('[[rule]]\nmatch = "deli"\naccount = "Expenses:Food"\n')
    mapping = "date=Date,payee=Description,amount=Amount"
    header = "Date,Description,Amount\n"
    _data(
        _import(
            book,
            "a.csv",
            header + "2026-01-05,Deli,3.00\n",
            "--account",
            "Liabilities:Card",
            "--csv",
            f"{mapping},sign=ledger",
            "--rules",
            str(rules),
        )
    )

    advised = _data(_import(book, "b.csv", header + "2026-02-05,Deli,2.00\n", "--csv", "sign=ledger"))

    assert advised["rows"][0]["payee"] == "Deli"
    assert "Expenses:Food" in advised["diff"]
    assert not any("Discarded remembered" in note for note in advised["notes"])
    (stored,) = _record(bea_config_dir)
    assert stored["mapping"] == mapping and stored["rules"] == str(rules.resolve())


def test_sign_bank_overrides_the_file_sign_ledger_was_chosen_for(book: Path) -> None:
    content = "Datum,Text,Betrag\n2026-01-05,Kaffee,3.00\n"
    ledger_signed = _data(
        _import(book, "a.csv", content, "--account", "Liabilities:Card", "--csv", f"{GERMAN},sign=ledger")
    )

    bank = _data(_import(book, "a.csv", content, "--csv", "sign=bank"))
    again = _data(_import(book, "a.csv", content))

    assert bank["rows"][0]["amount"] != ledger_signed["rows"][0]["amount"]
    assert again["rows"][0]["amount"] == bank["rows"][0]["amount"]


def test_an_encoding_key_alone_applies_over_memory_and_still_infers_without_it(book: Path) -> None:
    cp1252 = "Datum,Text,Betrag\n2026-02-05,Café,2.00\n".encode("cp1252")
    _data(
        _import(
            book,
            "a.csv",
            "Datum,Text,Betrag\n2026-01-05,Kaffee,3.00\n",
            "--account",
            "Liabilities:Card",
            "--csv",
            GERMAN,
        )
    )

    over_memory = _data(_import(book, "b.csv", cp1252, "--csv", "encoding=cp1252"))
    flag_free = _data(_import(book, "b.csv", cp1252))

    assert over_memory["config_source"] == "remembered --csv"
    assert over_memory["rows"][0]["narration"] == "Café"
    assert flag_free["rows"][0]["narration"] == "Café"


def test_a_key_only_csv_with_nothing_remembered_still_infers(book: Path) -> None:
    english = "Date,Description,Amount\n2026-02-05,Caf\xe9,2.00\n".encode("cp1252")

    inferred = _data(_import(book, "b.csv", english, "--csv", "encoding=cp1252", "--account", "Liabilities:Card"))
    unreadable = _import(book, "c.csv", "Datum,Text,Betrag\n2026-02-05,Tee,2.00\n", "--csv", "sign=ledger")

    assert inferred["config_source"] == "inferred --csv"
    assert inferred["rows"][0]["narration"] == "Café"
    assert unreadable.exit_code == 2
