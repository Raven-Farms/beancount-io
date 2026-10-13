"""A split ledger under a decomposed (NFD) directory name writes like any other (w5/144).

Ledger text is read as NFC, and that reached the include targets too — among
them the absolute paths `bea` writes into the staged copies it validates. The
loader then reported every included file under a respelled path that no
map-back table held, so `--allow-errors` took an error already in the books
for a new one, messages quoted a hidden `.bea-*.tmp` file, and a price already
quoted in another include went unseen.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

ROOT = """\
option "operating_currency" "USD"
2024-01-01 open Assets:Cash USD
2024-01-01 open Equity:Open USD
2024-01-01 open Expenses:Food USD
2024-01-01 commodity HOOL
include "{include}"
include "p-*.bean"
"""
YEAR = """\
2024-01-05 * "open"
  Assets:Cash  100 USD
  Equity:Open
2024-03-01 balance Assets:Cash  999 USD
"""
PRICES = "2024-02-01 price HOOL 10 USD\n"
NFC = unicodedata.normalize("NFC", "Buchführung")
NFD = unicodedata.normalize("NFD", NFC)
#: Where the root lives, where the included year file lives beside it, and the
#: include line that reaches it. The first is the control.
LAYOUTS = {
    "composed-parent": (NFC, "", "y2024.bean"),
    "decomposed-parent": (NFD, "", "y2024.bean"),
    "decomposed-subdirectory": ("books", NFD, f"{NFD}/y2024.bean"),
    "decomposed-subdirectory-glob": ("books", NFD, "*/y2024.bean"),
}


@pytest.fixture(params=sorted(LAYOUTS))
def books(request: pytest.FixtureRequest, tmp_path: Path, bea_config_dir: Path) -> tuple[Path, Path]:
    parent, subdirectory, include = LAYOUTS[request.param]
    assert len(NFD) == len(NFC) + 1
    directory = tmp_path / parent
    (directory / subdirectory).mkdir(parents=True)
    root = directory / "main.bean"
    root.write_text(ROOT.format(include=include), encoding="utf-8")
    year = directory / subdirectory / "y2024.bean"
    year.write_text(YEAR)
    (directory / "p-a.bean").write_text(PRICES)
    return root, year


def _bea(root: Path, *args: str) -> Any:
    return runner.invoke(app, ["--file", str(root), *args])


def _lunch(root: Path, *extra: str) -> Any:
    posting = ("-p", "Expenses:Food 3 USD", "-p", "Assets:Cash")
    return _bea(root, "add", "transaction", "--date", "2024-02-07", "--narration", "lunch", *posting, *extra)


def _warned_about_the_assertion(result: Any, year: Path) -> None:
    flat = " ".join(result.output.split())
    assert ".bea-" not in flat, flat
    assert f"{year}:4: Balance failed for 'Assets:Cash'" in flat, flat
    assert not [path for path in year.parents[1].rglob(".bea-*")]


def test_allow_errors_writes_into_the_included_file(books: tuple[Path, Path]) -> None:
    root, year = books

    result = _lunch(root, "--into", str(year.relative_to(root.parent)), "--allow-errors")

    assert result.exit_code == 0, result.output
    _warned_about_the_assertion(result, year)
    assert year.read_text().startswith(YEAR) and '* "lunch"' in year.read_text()


def test_allow_errors_writes_into_the_root(books: tuple[Path, Path]) -> None:
    root, year = books

    result = _lunch(root, "--allow-errors")

    assert result.exit_code == 0, result.output
    _warned_about_the_assertion(result, year)
    assert '* "lunch"' in root.read_text(encoding="utf-8") and year.read_text() == YEAR


def test_a_refused_write_names_the_included_file(books: tuple[Path, Path]) -> None:
    root, year = books

    result = _lunch(root, "--into", str(year.relative_to(root.parent)))

    assert result.exit_code == 1, result.output
    _warned_about_the_assertion(result, year)
    assert year.read_text() == YEAR


def test_a_price_quoted_in_another_include_still_conflicts(books: tuple[Path, Path]) -> None:
    root, _ = books
    new = root.parent / "p-b.bean"

    result = _bea(
        root,
        "add",
        "price",
        "--date",
        "2024-02-01",
        "-c",
        "HOOL",
        "--amount",
        "12 USD",
        "--into",
        new.name,
        "--allow-errors",
    )

    flat = " ".join(result.output.split())
    assert result.exit_code == 2, result.output
    assert "already has" in flat and "10 USD" in flat and ".bea-" not in flat, flat
    assert not new.exists()
