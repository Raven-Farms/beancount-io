"""A directory scan skips macOS AppleDouble `._name` files (w5/609).

macOS writes `._main.bean` beside `main.bean` on exFAT, FAT and SMB volumes,
and leaves such files in its archives. The scan took it for a ledger file:
`format --check .` and `format -i .` stopped with "Re-save the file as UTF-8"
and formatted nothing. A real ledger whose name starts `._` is still formatted.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
MISALIGNED = """2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD
2026-01-02 * "x"
  Expenses:Food 1 USD
  Assets:Cash
"""
APPLE_DOUBLE = b"\x00\x05\x16\x07\x00\x02\x00\x00Mac OS X        " + bytes(range(200, 256)) * 60


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(MISALIGNED)
    (tmp_path / "._main.bean").write_bytes(APPLE_DOUBLE)
    return tmp_path


def test_check_skips_the_apple_double_file(books: Path) -> None:
    result = runner.invoke(app, ["format", "--check", str(books)])

    assert result.exit_code == 1, result.output
    assert "main.bean" in result.output
    assert "._main.bean" not in result.output
    assert "UTF-8" not in result.output


def test_in_place_formats_the_ledger_and_leaves_the_apple_double_alone(books: Path) -> None:
    result = runner.invoke(app, ["format", "-i", str(books)])

    assert result.exit_code == 0, result.output
    assert (books / "main.bean").read_text() != MISALIGNED
    assert (books / "._main.bean").read_bytes() == APPLE_DOUBLE


def test_a_ledger_named_with_the_prefix_is_still_formatted(tmp_path: Path) -> None:
    (tmp_path / "._real.bean").write_text(MISALIGNED)

    result = runner.invoke(app, ["format", "-i", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "._real.bean").read_text() != MISALIGNED
