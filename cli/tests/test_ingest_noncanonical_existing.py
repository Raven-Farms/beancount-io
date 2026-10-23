"""Stock Beangulp must not silently miss duplicates in a BOM or NFD existing ledger (w5/704)."""

from __future__ import annotations

import shlex
import textwrap
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

pytestmark = pytest.mark.usefixtures("use_optional_engine")
ACCOUNT = "Assets:Bank:Épargne"
TRANSACTION = f'2026-01-09 * "Salary" ""\n  {ACCOUNT}  1000.00 USD\n  Income:Salary\n'
SCRIPT = textwrap.dedent(
    """\
    import csv
    from datetime import date
    from decimal import Decimal
    from pathlib import Path

    marker = Path(__file__).with_name("importer-ran.marker")
    with marker.open("a") as output:
        output.write("loaded\\n")

    from beancount.core import data
    from beancount.core.amount import Amount
    from beangulp import Ingest, Importer

    ACCOUNT = "Assets:Bank:Épargne"

    class BankImporter(Importer):
        @property
        def name(self):
            return "synthetic.BankImporter"

        def identify(self, filepath):
            return str(filepath).endswith(".csv")

        def account(self, filepath):
            return ACCOUNT

        def date(self, filepath):
            return date(2026, 1, 9)

        def filename(self, filepath):
            return Path(filepath).name

        def extract(self, filepath, existing):
            entries = []
            with open(filepath) as source:
                for lineno, row in enumerate(csv.DictReader(source), 2):
                    posting = data.Posting(ACCOUNT, Amount(Decimal(row["Amount"]), "USD"), None, None, None, None)
                    entries.append(data.Transaction(
                        data.new_metadata(filepath, lineno), date.fromisoformat(row["Date"]), "*",
                        row["Payee"], "", frozenset(), frozenset(), [posting],
                    ))
            return entries

    if __name__ == "__main__":
        Ingest([BankImporter()])()
    """
)


@dataclass
class Books:
    root: Path
    affected: Path
    script: Path
    source: Path
    marker: Path
    originals: dict[Path, bytes]


def _books(tmp_path: Path, *, kind: str, location: str) -> Books:
    directory = tmp_path / "books' saved"
    directory.mkdir()
    root = directory / "main ledger.bean"
    header = f'option "operating_currency" "USD"\n2026-01-01 open {ACCOUNT} USD\n2026-01-01 open Income:Salary USD\n'
    if location == "include":
        parts = directory / "parts"
        parts.mkdir()
        affected = parts / "January's ledger.bean"
        root.write_text(header + 'include "parts/*.bean"\n', encoding="utf-8")
        affected.write_text(TRANSACTION, encoding="utf-8")
    else:
        assert location == "root"
        affected = root
        root.write_text(header + "\n" + TRANSACTION, encoding="utf-8")
    if kind == "bom":
        affected.write_bytes(b"\xef\xbb\xbf" + affected.read_bytes())
    elif kind == "nfd":
        affected.write_text(unicodedata.normalize("NFD", affected.read_text()), encoding="utf-8")
    else:
        assert kind == "clean"
    script = tmp_path / "ingest config.py"
    script.write_text(SCRIPT, encoding="utf-8")
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    source = downloads / "bank-jan.csv"
    source.write_text("Date,Payee,Amount\n2026-01-03,Coffee,-4.50\n2026-01-09,Salary,1000.00\n")
    paths = {root, affected, script, source}
    return Books(
        root, affected, script, source, script.with_name("importer-ran.marker"), {p: p.read_bytes() for p in paths}
    )


def _extract(books: Books, *, spelling: str = "short", output: Path | None = None, existing: bool = True) -> Any:
    args = ["ingest", "extract", "--config", str(books.script)]
    if existing:
        args += {
            "short": ["-e", str(books.root)],
            "equals": [f"--existing={books.root}"],
            "clustered": ["-qe", str(books.root)],
        }[spelling]
    args += [str(books.source)]
    if output is not None:
        args += ["-o", str(output)]
    return CliRunner().invoke(app, args)


def _normal_engine(monkeypatch: pytest.MonkeyPatch, args: list[str]) -> Any:
    # The optional Beangulp interpreter intentionally has only its runtime
    # dependencies; ordinary check/format use the checkout's complete engine.
    with monkeypatch.context() as normal:
        normal.delenv("BEA_ENGINE_PYTHON", raising=False)
        return CliRunner().invoke(app, args)


def _duplicate(text: str, books: Books) -> None:
    assert "; duplicate of" in text, text
    assert books.affected.name in text, text
    assert "Salary" in text and "Coffee" in text


@pytest.mark.parametrize("kind", ["bom", "nfd"])
@pytest.mark.parametrize("location", ["root", "include"])
@pytest.mark.parametrize("spelling", ["short", "equals", "clustered"])
def test_noncanonical_existing_members_refuse_before_script_execution_or_partial_output(
    tmp_path: Path, kind: str, location: str, spelling: str
) -> None:
    books = _books(tmp_path, kind=kind, location=location)
    destination = None if spelling == "short" else tmp_path / "extract.bean"
    sentinel = b"; prior extraction must survive\n"
    if spelling == "clustered":
        assert destination is not None
        destination.write_bytes(sentinel)

    done = _extract(books, spelling=spelling, output=destination)

    assert done.exit_code == 2, done.output
    assert done.stdout == ""
    assert str(books.affected) in done.stderr
    assert "duplicate detection" in done.stderr and "Nothing was extracted" in done.stderr
    if kind == "bom":
        assert "UTF-8 BOM" in done.stderr and "bea format -i" in done.stderr
    else:
        assert "Re-save that file in Unicode NFC" in done.stderr
        assert "'bea format -i' does not normalize Unicode" in done.stderr
    assert not books.marker.exists()
    assert {p: p.read_bytes() for p in books.originals} == books.originals
    if destination is not None:
        if spelling == "clustered":
            assert destination.read_bytes() == sentinel
        else:
            assert not destination.exists()


@pytest.mark.parametrize("kind", ["bom", "nfd"])
@pytest.mark.parametrize("location", ["root", "include"])
def test_repairing_the_named_member_restores_real_beangulp_duplicate_detection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str, location: str
) -> None:
    books = _books(tmp_path, kind=kind, location=location)
    checked = _normal_engine(monkeypatch, ["--file", str(books.root), "check"])
    assert checked.exit_code == 0, checked.output
    refused = _extract(books)
    assert refused.exit_code == 2, refused.output
    assert not books.marker.exists()
    if kind == "bom":
        # Execute the actual shell-quoted remedy, including spaces and an
        # apostrophe in both root and included-member path spellings.
        printed = refused.stderr.split("Run ", 1)[1].split(" to strip the mark", 1)[0]
        command = shlex.split(printed)
        assert command == ["bea", "format", "-i", str(books.affected)]
        formatted = _normal_engine(monkeypatch, command[1:])
        assert formatted.exit_code == 0, formatted.output
        assert not books.affected.read_bytes().startswith(b"\xef\xbb\xbf")
    else:
        books.affected.write_text(unicodedata.normalize("NFC", books.affected.read_text()), encoding="utf-8")

    extracted = _extract(books)

    assert extracted.exit_code == 0, extracted.output
    _duplicate(extracted.stdout, books)
    assert books.marker.read_text() == "loaded\n"
    assert books.source.read_bytes() == books.originals[books.source]
    assert books.script.read_bytes() == books.originals[books.script]


def test_a_clean_nfc_existing_ledger_still_marks_the_real_duplicate_in_export_output(tmp_path: Path) -> None:
    books = _books(tmp_path, kind="clean", location="include")
    destination = tmp_path / "extract.bean"
    destination.write_text("; an earlier extract\n")

    done = _extract(books, output=destination)

    assert done.exit_code == 0, done.output
    _duplicate(destination.read_text(), books)
    assert books.marker.read_text() == "loaded\n"
    assert {p: p.read_bytes() for p in books.originals} == books.originals


@pytest.mark.parametrize("bom_at", ["lexical-include", "physical-include"])
def test_a_symlinked_existing_root_uses_the_same_lexical_include_directory_as_beangulp(
    tmp_path: Path, bom_at: str
) -> None:
    books = _books(tmp_path, kind="clean", location="include")
    linked = tmp_path / "linked books"
    (linked / "parts").mkdir(parents=True)
    root = linked / "main ledger.bean"
    root.symlink_to(books.root)
    member = linked / "parts" / "logical January.bean"
    member.write_text(TRANSACTION, encoding="utf-8")
    affected = member if bom_at == "lexical-include" else books.affected
    affected.write_bytes(b"\xef\xbb\xbf" + affected.read_bytes())
    originals = {p: p.read_bytes() for p in {*books.originals, root, member}}
    via_link = Books(root, member, books.script, books.source, books.marker, originals)

    done = _extract(via_link)

    if bom_at == "lexical-include":
        assert done.exit_code == 2, done.output
        assert str(member) in done.stderr and "UTF-8 BOM" in done.stderr
        assert done.stdout == "" and not books.marker.exists()
    else:
        assert done.exit_code == 0, done.output
        _duplicate(done.stdout, via_link)
        assert books.marker.read_text() == "loaded\n"
    assert {p: p.read_bytes() for p in originals} == originals


@pytest.mark.parametrize("operation", ["extract", "identify", "archive"])
def test_other_ingest_operations_do_not_scan_an_unused_noncanonical_ledger(tmp_path: Path, operation: str) -> None:
    books = _books(tmp_path, kind="nfd", location="root")
    args = ["--file", str(books.root), "ingest", operation, "--config", str(books.script), str(books.source)]
    if operation == "archive":
        documents = tmp_path / "documents"
        documents.mkdir()
        args += ["--dry-run", "-o", str(documents)]

    done = CliRunner().invoke(app, args)

    assert done.exit_code == 0, done.output
    assert "not Unicode NFC" not in done.output
    assert books.marker.read_text() == "loaded\n"
    assert {p: p.read_bytes() for p in books.originals} == books.originals
    if operation == "extract":
        assert "Salary" in done.stdout and "; duplicate of" not in done.stdout
