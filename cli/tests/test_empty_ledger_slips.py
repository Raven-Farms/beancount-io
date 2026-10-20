"""Two empty-ledger slips (w5/843).

`list`'s empty-result notice went to stdout, unlike `query`'s `(no rows)` and
`balance`'s notice, so a pipeline read it as a row; and a file holding only a
UTF-8 BOM got two newlines before its first appended entry, a zero-byte file one.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


@pytest.mark.parametrize(
    ("args", "notice"),
    [(["list", "price"], "No prices found."), (["list", "transaction", "--details"], "No transactions found.")],
)
def test_an_empty_list_says_so_on_stderr(tmp_path: Path, args: list[str], notice: str) -> None:
    ledger = tmp_path / "z.bean"
    ledger.write_bytes(b"")

    result = runner.invoke(app, ["--file", str(ledger), *args])

    assert result.exit_code == 0, result.output
    assert result.stdout == ""
    assert result.stderr == f"{notice}\n"


@pytest.mark.parametrize("start", [b"", b"\xef\xbb\xbf"], ids=["zero-byte", "bom-only"])
def test_a_bom_only_file_takes_its_first_entry_like_an_empty_one(tmp_path: Path, start: bytes) -> None:
    ledger = tmp_path / "z.bean"
    ledger.write_bytes(start)

    result = runner.invoke(
        app, ["--file", str(ledger), "add", "open", "--date", "2026-01-01", "--account", "Assets:Cash", "-c", "USD"]
    )

    assert result.exit_code == 0, result.output
    assert ledger.read_bytes() == start + b"\n2026-01-01 open Assets:Cash USD\n"
    assert runner.invoke(app, ["--file", str(ledger), "check"]).exit_code == 0
