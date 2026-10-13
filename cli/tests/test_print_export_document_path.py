"""A `PRINT` export keeps a document path portable (w5/229).

The loader makes every document path absolute and the export printed it that
way: the file named the machine it ran on, failed `bea check` once saved
outside the ledger directory, and was refused by `price export` beside it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

LEDGER = """\
2026-01-01 open Assets:Cash
2026-01-05 document Assets:Cash "{path}"
2026-01-06 note Assets:Cash "control"
"""


def _books(tmp_path: Path, path: str = "receipts/r.pdf") -> Path:
    books = tmp_path / "books"
    (books / "receipts").mkdir(parents=True)
    (books / "receipts" / "r.pdf").write_bytes(b"%PDF")
    (books / "main.bean").write_text(LEDGER.format(path=path))
    return books


def _bea(*args: str, code: int = 0) -> str:
    result = runner.invoke(app, list(args))
    assert result.exit_code == code, result.output
    return result.output


def _export(ledger: Path, out: Path, query: str = "PRINT") -> str:
    _bea("--file", str(ledger), "query", query, "-f", "beancount", "-o", str(out))
    return out.read_text()


def test_an_export_saved_elsewhere_keeps_the_relative_path(tmp_path: Path, bea_config_dir: Path) -> None:
    books = _books(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    exported = _export(books / "main.bean", elsewhere / "out.bean")

    assert '2026-01-05 document Assets:Cash "receipts/r.pdf"' in exported
    assert str(tmp_path) not in exported


def test_an_export_beside_the_ledger_passes_check_and_price_export(tmp_path: Path, bea_config_dir: Path) -> None:
    books = _books(tmp_path)

    _export(books / "main.bean", books / "beside.bean")

    _bea("--file", str(books / "beside.bean"), "check")
    _bea("--file", str(books / "beside.bean"), "price", "export")
    assert (books / "beside-export" / "receipts" / "r.pdf").read_bytes() == b"%PDF"


def test_the_terminal_print_names_the_same_path(tmp_path: Path, bea_config_dir: Path) -> None:
    books = _books(tmp_path)

    printed = _bea("--file", str(books / "main.bean"), "query", "PRINT")

    assert '"receipts/r.pdf"' in printed
    assert str(tmp_path) not in printed


def test_a_path_written_in_an_included_file_is_respelled_from_the_root(tmp_path: Path, bea_config_dir: Path) -> None:
    books = _books(tmp_path)
    (books / "year").mkdir()
    (books / "year" / "entries.bean").write_text('2026-01-05 document Assets:Cash "../receipts/r.pdf"\n')
    (books / "main.bean").write_text('2026-01-01 open Assets:Cash\ninclude "year/entries.bean"\n')

    exported = _export(books / "main.bean", books / "beside.bean")

    assert '2026-01-05 document Assets:Cash "receipts/r.pdf"' in exported
    _bea("--file", str(books / "beside.bean"), "check")


def test_a_ledger_opened_through_a_symlink_exports_the_same_path(tmp_path: Path, bea_config_dir: Path) -> None:
    books = _books(tmp_path)
    link = tmp_path / "link"
    try:
        link.symlink_to(books, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks are not available")

    exported = _export(link / "main.bean", tmp_path / "out.bean")

    assert '2026-01-05 document Assets:Cash "receipts/r.pdf"' in exported


def test_a_document_outside_the_ledger_directory_stays_absolute(tmp_path: Path, bea_config_dir: Path) -> None:
    outside = tmp_path / "outside" / "o.pdf"
    outside.parent.mkdir()
    outside.write_bytes(b"%PDF")
    books = _books(tmp_path, path=str(outside))

    exported = _export(books / "main.bean", books / "beside.bean")

    assert f'2026-01-05 document Assets:Cash "{outside}"' in exported


def test_an_export_without_documents_is_unchanged(tmp_path: Path, bea_config_dir: Path) -> None:
    books = _books(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    exported = _export(books / "main.bean", elsewhere / "ctl.bean", "PRINT FROM type != 'document'")

    assert exported == '2026-01-01 open Assets:Cash\n\n2026-01-06 note Assets:Cash "control"\n'
    _bea("--file", str(elsewhere / "ctl.bean"), "check")
