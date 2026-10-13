"""The settings `bea import` echoes are shell words, so the line pastes back (w5/195).

The inferred mapping is printed as a ready-to-paste option string. Bank headers
such as "Posting Date" carry spaces, and the echo interpolated them unquoted:
pasting the line back failed with "unexpected extra argument(s)". The same held
for the ambiguity example, a date format with spaces and a remembered `--rules`
path with a space.
"""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

LEDGER = (
    'option "operating_currency" "USD"\n'
    "2020-01-01 open Assets:Checking USD\n"
    "2020-01-01 open Expenses:Food\n"
    "2020-01-01 open Expenses:Uncategorized\n"
)
SPACED = "Posting Date,Transaction Description,Amount\n03/13/2024,Coffee Shop,-4.50\n03/14/2024,Grocer,-20.00\n"
SPACED_SPEC = "date=Posting Date,amount=Amount,narration=Transaction Description"
INFERRED = "Read the column mapping from the header row: "


@pytest.fixture
def book(tmp_path: Path, bea_config_dir: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    return ledger


def _import(book: Path, source: Path, *args: str, ok: bool = True) -> Any:
    result = runner.invoke(app, ["--json", "--no-input", "--file", str(book), "import", str(source), *args])
    if ok:
        assert result.exit_code == 0, result.output
        return json.loads(result.stdout)["data"]
    return result


def _note(data: Any, prefix: str) -> str:
    (note,) = [line for line in data["notes"] if line.startswith(prefix)]
    return str(note)


def _echoed(data: Any) -> str:
    """The option string of the inferred-mapping note, without the sentence around it."""
    found = re.fullmatch(re.escape(INFERRED) + r"(.+)\. Pass --csv to override\.", _note(data, INFERRED))
    assert found is not None
    return found.group(1)


def test_spaced_headers_are_echoed_as_one_shell_word_and_paste_back(book: Path) -> None:
    source = book.parent / "bank2.csv"
    source.write_text(SPACED)

    inferred = _import(book, source, "--account", "Assets:Checking")
    echoed = _echoed(inferred)
    pasted = _import(book, source, "--account", "Assets:Checking", *shlex.split(echoed))

    assert echoed == f"--csv '{SPACED_SPEC}' --date-format %m/%d/%Y"
    assert shlex.split(echoed) == ["--csv", SPACED_SPEC, "--date-format", "%m/%d/%Y"]
    assert pasted["diff"] == inferred["diff"] and "2024-03-13" in pasted["diff"]
    assert any(note.startswith("Using column mapping (--csv") for note in pasted["notes"])


def test_the_text_note_carries_the_same_quoted_line(book: Path) -> None:
    source = book.parent / "bank2.csv"
    source.write_text(SPACED)

    result = runner.invoke(
        app, ["--no-input", "--file", str(book), "import", str(source), "--account", "Assets:Checking"]
    )

    assert result.exit_code == 0, result.output
    assert f"{INFERRED}--csv '{SPACED_SPEC}' --date-format %m/%d/%Y. Pass --csv to override." in " ".join(
        result.output.split()
    )


def test_space_free_headers_are_echoed_unquoted_as_before(book: Path) -> None:
    source = book.parent / "plain.csv"
    source.write_text("Date,Description,Amount\n2024-03-13,Coffee,-4.50\n")

    data = _import(book, source, "--account", "Assets:Checking")

    assert _echoed(data) == "--csv date=Date,amount=Amount,narration=Description --date-format %Y-%m-%d"


def test_a_detected_delimiter_stays_quoted_once_beside_spaced_headers(book: Path) -> None:
    source = book.parent / "semi.csv"
    source.write_text(SPACED.replace(",", ";"))
    plain = book.parent / "plain.csv"
    plain.write_text("Date;Description;Amount\n2024-03-13;Coffee;-4.50\n")

    inferred = _import(book, source, "--account", "Assets:Checking")
    echoed = _echoed(inferred)
    pasted = _import(book, source, "--account", "Assets:Checking", *shlex.split(echoed))

    assert echoed == f"--csv '{SPACED_SPEC}',delimiter=';' --date-format %m/%d/%Y"
    assert shlex.split(echoed)[1] == f"{SPACED_SPEC},delimiter=;"
    assert pasted["diff"] == inferred["diff"] and "2024-03-14" in pasted["diff"]
    # Control: the space-free spelling of the same echo is untouched.
    assert _echoed(_import(book, plain, "--account", "Assets:Checking")) == (
        "--csv date=Date,amount=Amount,narration=Description,delimiter=';' --date-format %Y-%m-%d"
    )


def test_the_ambiguity_example_is_one_shell_word(book: Path) -> None:
    source = book.parent / "two.csv"
    source.write_text(
        "Posting Date,Transaction Date,Transaction Description,Amount\n03/13/2024,03/12/2024,Coffee,-4.50\n"
    )

    refused = _import(book, source, "--csv", "auto", "--account", "Assets:Checking", ok=False)

    assert refused.exit_code == 2
    (example,) = re.findall(r"For example: (--csv .+)", " ".join((refused.stdout + refused.stderr).split()))
    words = shlex.split(example.split('"')[0])
    assert words[0] == "--csv" and len(words) == 2
    assert "date=Posting Date" in words[1] and "narration=Transaction Description" in words[1]
    pasted = _import(book, source, "--account", "Assets:Checking", *words)
    assert "2024-03-13" in pasted["diff"]


def test_remembered_settings_quote_a_spaced_date_format_and_rules_path(book: Path) -> None:
    source = book.parent / "bank3.csv"
    source.write_text("Posting Date,Transaction Description,Amount\n13 Mar 2024,Coffee Shop,-4.50\n")
    rules_dir = book.parent / "my rules"
    rules_dir.mkdir()
    rules = rules_dir / "rules.toml"
    rules.write_text('[[rule]]\nmatch = "Coffee"\naccount = "Expenses:Food"\n')
    typed = ["--csv", SPACED_SPEC, "--date-format", "%d %b %Y", "--rules", str(rules)]
    first = _import(book, source, "--account", "Assets:Checking", *typed)

    recalled = _import(book, source)
    prefix = "Using remembered settings for bank3.csv: "
    settings = _note(recalled, prefix).removeprefix(prefix).removesuffix(".")
    replayed = _import(book, source, "--account", "Assets:Checking", *shlex.split(settings))

    assert settings == f"--csv '{SPACED_SPEC}' --date-format '%d %b %Y' --rules {shlex.quote(str(rules.resolve()))}"
    assert shlex.split(settings) == ["--csv", SPACED_SPEC, "--date-format", "%d %b %Y", "--rules", str(rules.resolve())]
    assert replayed["diff"] == first["diff"] and "Expenses:Food" in replayed["diff"]

    # A fresh `--csv` drops what it does not repeat; the dropped flags are named as shell words too.
    dropped = _import(book, source, "--account", "Assets:Checking", "--csv", SPACED_SPEC)
    discarded = _note(dropped, "Discarded remembered settings for bank3.csv: ")
    assert f"--rules {shlex.quote(str(rules.resolve()))}" in discarded
