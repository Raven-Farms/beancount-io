"""Root-name scans use the loader's text normalization and option validation (w5/710)."""

from __future__ import annotations

import unicodedata
from pathlib import Path

import pytest

from bea_engine.ledger.text import root_name_options, root_names_of


@pytest.mark.parametrize("bom", ["", "\ufeff"], ids=["plain", "bom"])
@pytest.mark.parametrize("form", ["NFC", "NFD"])
@pytest.mark.parametrize("ending", ["", "\n"], ids=["eof", "newline"])
def test_root_names_normalize_like_the_loader(tmp_path: Path, bom: str, form: str, ending: str) -> None:
    value = unicodedata.normalize(form, "Vermögen")
    text = f'{bom}option "name_assets" "{value}"{ending}'
    ledger = tmp_path / "main.bean"
    ledger.write_text(text, encoding="utf-8")

    assert root_name_options(text) == {"name_assets": "Vermögen"}
    assert root_names_of(ledger) == ("Vermögen", "Liabilities", "Equity", "Income", "Expenses")


@pytest.mark.parametrize("invalid", ["assets", "", "Bad:Root", "Two Words"])
def test_invalid_values_retain_the_last_valid_root(invalid: str) -> None:
    assert root_name_options(f'option "name_assets" "{invalid}"\n') == {}
    assert root_name_options(
        f'option "name_assets" "Actif"\noption "name_assets" "Aktiva"\noption "name_assets" "{invalid}"\n'
    ) == {"name_assets": "Aktiva"}


def test_valid_replacements_preserve_option_insertion_order() -> None:
    options = root_name_options(
        'option "name_expenses" "Aufwand"\n'
        'option "name_assets" "Actif"\n'
        'option "name_expenses" "Kosten"\n'
        'option "name_equity" "Kapital"\n'
    )

    assert list(options.items()) == [
        ("name_expenses", "Kosten"),
        ("name_assets", "Actif"),
        ("name_equity", "Kapital"),
    ]


@pytest.mark.parametrize(
    "source",
    [
        'option"name_assets""Aktiva"',
        'option "name_assets" "Aktiva" ; trailing comment',
        r'option "name_asset\s" "Akt\iva"',
    ],
    ids=["touching-strings", "comment", "lexer-escapes"],
)
def test_lexer_spellings_are_read_as_option_values(source: str) -> None:
    assert root_name_options(source) == {"name_assets": "Aktiva"}


def test_comments_quoted_text_and_malformed_lines_do_not_replace_a_valid_option() -> None:
    text = (
        'option "name_assets" "Aktiva"\n'
        '; option "name_assets" "Comment"\n'
        '2026-01-01 * "option \\"name_assets\\" \\"Narration\\""\n'
        'option "name_assets" "Trailing" "extra"\n'
        'option "name_assets"\n'
        'option "operating_currency" "USD"\n'
    )
    assert root_name_options(text) == {"name_assets": "Aktiva"}


def test_unreadable_root_retains_the_default_names(tmp_path: Path) -> None:
    assert root_names_of(tmp_path / "missing.bean") == ("Assets", "Liabilities", "Equity", "Income", "Expenses")
