"""An imported document with a relative attachment path skips on repeat (w5/917).

The loader resolves a relative document filename against the file holding the
directive, so the ledger's copy was absolute and never matched the importer's
relative spelling: three unchanged imports wrote three document lines.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_import_source_facts import _bea, _written

IMPORTER = """import datetime
import json
from pathlib import Path
from beancount.core import data

class Statement:
    def identify(self, path): return path.endswith(".json")
    def account(self, path): return "Assets:Cash"
    def extract(self, path, existing):
        filename = json.loads(Path(path).read_text())["filename"]
        return [data.Document(data.new_metadata(path, 1), datetime.date(2024, 2, 1), "Assets:Cash", filename,
                              frozenset({"statement"}), frozenset({"jan2024"}))]

CONFIG = [Statement()]
"""


def _books(tmp_path: Path, filename: str, *, included: bool) -> tuple[Path, list[str]]:
    books = tmp_path / "books"
    (books / "receipts").mkdir(parents=True)
    (books / "receipts" / "statement.txt").write_text("synthetic\n")
    main = books / "main.bean"
    flags = ["--apply"]
    if included:
        (books / "entries").mkdir()
        (books / "entries" / "statements.bean").write_text("; statements\n")
        main.write_text('include "entries/statements.bean"\n2024-01-01 open Assets:Cash USD\n')
        flags += ["--into", str(books / "entries" / "statements.bean")]
    else:
        main.write_text("2024-01-01 open Assets:Cash USD\n")
    (tmp_path / "importers.py").write_text(IMPORTER)
    (tmp_path / "statement.json").write_text(json.dumps({"filename": filename}))
    return main, flags


def _import(tmp_path: Path, main: Path, flags: list[str]) -> int:
    result = _bea(
        tmp_path,
        "import",
        str(tmp_path / "statement.json"),
        "--config",
        str(tmp_path / "importers.py"),
        *flags,
        ledger=str(main.relative_to(tmp_path)),
    )
    return _written(result)


@pytest.mark.parametrize("included", [False, True], ids=["root", "included"])
@pytest.mark.parametrize("spelling", ["receipts/statement.txt", "./receipts/statement.txt", "ABSOLUTE"])
def test_an_unchanged_document_writes_once(tmp_path: Path, spelling: str, included: bool) -> None:
    books = tmp_path / "books"
    filename = str(books / "receipts" / "statement.txt") if spelling == "ABSOLUTE" else spelling
    if included and spelling != "ABSOLUTE":
        filename = "../" + spelling.removeprefix("./")
    main, flags = _books(tmp_path, filename, included=included)

    written = [_import(tmp_path, main, flags) for _ in range(3)]

    assert written == [1, 0, 0]
    target = books / "entries" / "statements.bean" if included else main
    assert filename in target.read_text()
    assert _bea(tmp_path, "check", ledger=str(main.relative_to(tmp_path))).returncode == 0


def test_a_different_attachment_path_is_a_new_document(tmp_path: Path) -> None:
    main, flags = _books(tmp_path, "receipts/statement.txt", included=False)
    (tmp_path / "books" / "other").mkdir()
    (tmp_path / "books" / "other" / "statement.txt").write_text("synthetic\n")
    assert _import(tmp_path, main, flags) == 1

    (tmp_path / "statement.json").write_text('{"filename": "other/statement.txt"}')

    assert _import(tmp_path, main, flags) == 1
