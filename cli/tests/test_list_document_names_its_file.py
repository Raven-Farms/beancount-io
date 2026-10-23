"""`list document` names the file each row's path is relative to (w5/833).

A filename is relative to the include that wrote the directive (w5/066), but
the row never named that file: two includes' `receipt.pdf` listed alike and
neither resolved from the root.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


def _books(tmp_path: Path) -> Path:
    for year in ("2025", "2026"):
        (tmp_path / year).mkdir()
        (tmp_path / year / "books.bean").write_text(f'{year}-03-01 document Assets:Cash "receipt.pdf"\n')
        (tmp_path / year / "receipt.pdf").write_bytes(b"%PDF")
    root = tmp_path / "main.bean"
    root.write_text('2025-01-01 open Assets:Cash\ninclude "2025/books.bean"\ninclude "2026/books.bean"\n')
    return root


def test_json_rows_carry_their_source(tmp_path: Path) -> None:
    root = _books(tmp_path)

    result = runner.invoke(app, ["--json", "--file", str(root), "list", "document"])

    assert result.exit_code == 0, result.output
    rows = json.loads(result.stdout)["data"]
    assert [(row["filename"], row["source"]) for row in rows] == [
        ("receipt.pdf", {"filename": str(tmp_path / "2025" / "books.bean"), "lineno": 1}),
        ("receipt.pdf", {"filename": str(tmp_path / "2026" / "books.bean"), "lineno": 1}),
    ]
    for row in rows:
        assert (Path(row["source"]["filename"]).parent / row["filename"]).is_file()


def test_the_table_names_the_writing_file(tmp_path: Path) -> None:
    root = _books(tmp_path)

    result = runner.invoke(app, ["--file", str(root), "list", "document"])

    assert result.exit_code == 0, result.output
    assert "WRITTEN IN" in result.stdout
    assert "2025/books.bean:1" in result.stdout and "2026/books.bean:1" in result.stdout
