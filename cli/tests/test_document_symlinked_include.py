"""Document containment uses the include's named directory (w5/653)."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


@pytest.mark.parametrize("filename", ["receipt.pdf", "../../outside.pdf", "outside-link.pdf"])
@pytest.mark.parametrize("absolute_into", [False, True])
def test_document_in_symlinked_include_uses_lexical_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, filename: str, absolute_into: bool
) -> None:
    books = tmp_path / "books"
    (books / "txns").mkdir(parents=True)
    root = books / "main.bean"
    root.write_text('option "operating_currency" "USD"\n2026-01-01 open Assets:Checking USD\ninclude "txns/*.bean"\n')
    target = tmp_path / "shared/a/b/link.bean"
    target.parent.mkdir(parents=True)
    target.write_text("2026-01-01 open Equity:Opening USD\n")
    linked = books / "txns/link.bean"
    linked.symlink_to(target)
    (books / "txns/receipt.pdf").write_bytes(b"%PDF receipt\n")
    # The out-of-tree case must be refused even if the referenced file exists.
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"%PDF outside\n")
    (books / "txns/outside-link.pdf").symlink_to(outside)
    original = target.read_bytes()
    root_before = root.read_bytes()
    monkeypatch.chdir(books)

    result = runner.invoke(
        app,
        [
            "--json",
            "--file",
            str(root),
            "add",
            "document",
            "--into",
            str(linked) if absolute_into else "txns/link.bean",
            "--date",
            "2026-02-01",
            "-a",
            "Assets:Checking",
            "--path",
            filename,
        ],
    )

    if filename == "receipt.pdf":
        assert result.exit_code == 0, result.output
        assert 'document Assets:Checking "receipt.pdf"' in target.read_text()
        checked = runner.invoke(app, ["--json", "--file", str(root), "check"])
        assert checked.exit_code == 0, checked.output
    else:
        assert result.exit_code == 2, result.output
        assert "outside the ledger directory" in result.output
        assert target.read_bytes() == original
    assert linked.is_symlink()
    assert root.read_bytes() == root_before
