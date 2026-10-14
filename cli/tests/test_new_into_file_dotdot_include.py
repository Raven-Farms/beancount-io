"""The first write into a not-yet-existing `--into` file still sees a `../` include (w5/291).

A planned destination that is not on disk routes the load through staged
twins. While the snapshot kept `books/../shared/prices.bean` as written, the
loader named that file's entries and errors by the normalized path of its
twin, the map back to the original missed, and the entries read as
plugin-generated: `add price` wrote a conflicting or duplicate quote, and
`--allow-errors` refused over the error it was told to tolerate. No managed
price include is involved.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

ROOT = """\
option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Uncategorized
2026-01-01 open Equity:Opening
2026-01-02 * "Open"
  Assets:Checking  100.00 USD
  Equity:Opening
include "{include}"
include "2026/*.bean"
"""
PRICES = """\
2026-01-01 commodity HOOL
2026-02-10 price HOOL 110.00 USD
"""
ASSERTION = "2026-01-24 balance Assets:Checking  5.00 USD\n"
JANUARY = '2026-01-03 event "location" "NYC"\n'
# The shared file outside the root's directory, and the same books with it inside.
LAYOUTS = {"dotdot": ("..", "../shared/prices.bean"), "plain": (".", "shared/prices.bean")}
# The absent period file, and the existing one that never took the staged load.
DESTINATIONS = {"absent": "2026/02.bean", "existing": "2026/01.bean"}


@pytest.fixture(params=sorted(LAYOUTS))
def books(request: pytest.FixtureRequest, tmp_path: Path, bea_config_dir: Path) -> tuple[Path, Path]:
    shared_home, include = LAYOUTS[request.param]
    home = tmp_path / "books"
    (home / "2026").mkdir(parents=True)
    root = home / "main.bean"
    root.write_text(ROOT.format(include=include))
    (home / "2026" / "01.bean").write_text(JANUARY)
    shared = (home / shared_home).resolve() / "shared" / "prices.bean"
    shared.parent.mkdir()
    shared.write_text(PRICES)
    return root, shared


def _bea(root: Path, *args: str) -> Any:
    return runner.invoke(app, ["--file", str(root), *args])


def _price(root: Path, amount: str, into: str) -> Any:
    return _bea(
        root, "--json", "add", "price", "--date", "2026-02-10", "-c", "HOOL", "--amount", amount, "--into", into
    )


def _untouched(root: Path, shared: Path) -> None:
    year = root.parent / "2026"
    assert sorted(path.name for path in year.iterdir()) == ["01.bean"]
    assert (year / "01.bean").read_text() == JANUARY
    assert not list(shared.parent.glob(".bea-*"))


@pytest.mark.parametrize("into", sorted(DESTINATIONS))
def test_a_different_quote_for_the_day_is_refused_naming_the_shared_file(books: tuple[Path, Path], into: str) -> None:
    root, shared = books

    result = _price(root, "111 USD", DESTINATIONS[into])

    assert result.exit_code == 2, result.output
    flat = " ".join(result.output.split())
    assert f"HOOL already has a 2026-02-10 price of 110.00 USD (at {shared}:2); refusing 111 USD" in flat
    _untouched(root, shared)


@pytest.mark.parametrize("into", sorted(DESTINATIONS))
def test_the_same_quote_is_a_duplicate_and_writes_nothing(books: tuple[Path, Path], into: str) -> None:
    root, shared = books

    result = _price(root, "110.00 USD", DESTINATIONS[into])

    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)["data"]
    assert (data["written"], data["duplicate"]) == (0, True)
    assert data["source"] == {"filename": str(shared), "lineno": 2}
    _untouched(root, shared)


@pytest.mark.parametrize("into", sorted(DESTINATIONS))
def test_allow_errors_writes_over_the_assertion_already_in_the_shared_file(books: tuple[Path, Path], into: str) -> None:
    root, shared = books
    shared.write_text(PRICES + ASSERTION)
    dest = root.parent / DESTINATIONS[into]

    result = _bea(
        root,
        "add",
        "note",
        "--date",
        "2026-03-01",
        "-a",
        "Assets:Checking",
        "-m",
        "new month",
        "--into",
        DESTINATIONS[into],
        "--allow-errors",
    )

    assert result.exit_code == 0, result.output
    flat = " ".join(result.output.split())
    assert f"{shared}:3: Balance failed for 'Assets:Checking'" in flat
    assert "new ledger error" not in flat and ".bea-" not in flat and "/../" not in flat, flat
    assert '2026-03-01 note Assets:Checking "new month"' in dest.read_text()
    assert shared.read_text() == PRICES + ASSERTION
