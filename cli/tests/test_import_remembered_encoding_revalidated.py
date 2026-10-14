"""A remembered `encoding=` is re-validated against each new file (w5/281).

One Windows export is imported with `encoding=cp1252`; the bank's next
export, same header, is UTF-8. The flag-free import decoded it with the
remembered codec and wrote `CafÃ© ZÃ¼rich` to the ledger with exit 0.
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
    'option "operating_currency" "USD"\n2026-01-01 open Assets:Checking USD\n2026-01-01 open Expenses:Uncategorized\n'
)
MAPPING = "date=Date,amount=Amount,narration=Description"
HEADER = "Date,Description,Amount\n"


@pytest.fixture
def book(tmp_path: Path, bea_config_dir: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    return ledger


def _import(book: Path, name: str, content: bytes, *args: str) -> Any:
    source = book.parent / name
    source.write_bytes(content)
    result = runner.invoke(app, ["--json", "--no-input", "--file", str(book), "import", str(source), *args])
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)["data"]


def _remember_cp1252(book: Path, codec: str = "cp1252") -> None:
    first = _import(
        book,
        "jan.csv",
        (HEADER + "2026-01-05,Café Zürich,-3.00\n").encode(codec),
        "--csv",
        f"{MAPPING},encoding={codec}",
        "--account",
        "Assets:Checking",
        "--apply",
    )
    assert first["rows"][0]["narration"] == "Café Zürich"


def _stored_mapping(config: Path) -> str:
    (record,) = (config / "importers").glob("csv-*.json")
    (stored,) = json.loads(record.read_text())["sources"]
    return str(stored["mapping"])


@pytest.mark.parametrize("codec", ["cp1252", "latin-1"])
def test_a_utf8_export_is_not_decoded_with_the_remembered_codec(book: Path, bea_config_dir: Path, codec: str) -> None:
    _remember_cp1252(book, codec)

    feb = _import(book, "feb.csv", (HEADER + "2026-02-05,Café Zürich,-4.00\n").encode(), "--apply")

    assert feb["config_source"] == "remembered --csv"
    assert feb["rows"][0]["narration"] == "Café Zürich"
    assert feb["written"] == 1
    assert '2026-02-05 ! "Café Zürich"' in book.read_text()
    assert "Ã" not in book.read_text()
    assert feb["remembered"]["encoding"] == "utf-8"
    assert any(f"Remembered --csv encoding={codec} does not match feb.csv" in note for note in feb["notes"])
    assert not any(f"--csv encoding={codec}." in note for note in feb["notes"])
    # Only that run changed: the saved mapping still names the codec.
    assert _stored_mapping(bea_config_dir) == f"{MAPPING},encoding={codec}"


def test_a_utf8_export_with_a_bom_matches_the_remembered_header(book: Path) -> None:
    _remember_cp1252(book)

    bom = _import(book, "bom.csv", b"\xef\xbb\xbf" + (HEADER + "2026-03-05,Café Zürich,-5.00\n").encode())

    assert bom["rows"][0]["narration"] == "Café Zürich"
    assert bom["remembered"]["encoding"] == "utf-8"


def test_a_later_cp1252_export_is_still_read_with_the_remembered_codec(book: Path) -> None:
    _remember_cp1252(book)
    _import(book, "feb.csv", (HEADER + "2026-02-05,Café Zürich,-4.00\n").encode(), "--apply")

    mar = _import(book, "mar.csv", (HEADER + "2026-04-05,Café Genève,-6.00\n").encode("cp1252"), "--apply")

    assert mar["rows"][0]["narration"] == "Café Genève"
    assert mar["remembered"]["encoding"] == "cp1252"
    assert any("--csv encoding=cp1252." in note for note in mar["notes"])
    assert not any("does not match" in note for note in mar["notes"])


def test_an_ascii_export_keeps_the_remembered_codec_silently(book: Path) -> None:
    _remember_cp1252(book)

    plain = _import(book, "plain.csv", (HEADER + "2026-05-05,Plain,-7.00\n").encode())

    assert plain["rows"][0]["narration"] == "Plain"
    assert plain["remembered"]["encoding"] == "cp1252"
    assert not any("does not match" in note for note in plain["notes"])


def test_a_fresh_utf8_import_is_the_control(book: Path) -> None:
    feb = _import(
        book,
        "feb.csv",
        (HEADER + "2026-02-05,Café Zürich,-4.00\n").encode(),
        "--account",
        "Assets:Checking",
        "--apply",
    )

    assert feb["rows"][0]["narration"] == "Café Zürich"
    assert '2026-02-05 ! "Café Zürich"' in book.read_text()
