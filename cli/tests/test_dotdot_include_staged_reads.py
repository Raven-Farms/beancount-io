"""A file included through `..` keeps its own name on every staged load (w5/285, w5/291).

Two loads parse staged twins of the whole closure rather than the files
themselves: a read of a ledger with a managed price include, and the
validation of a first write into a destination that does not exist yet. The
snapshot kept `2026/../shared/prices.bean` as written while the loader named
the twin by its normalized path, so the map back to the originals missed.
The shared file's entries then carried a vanished `.bea-*.tmp` name: they
read as generated, `list --on-disk` hid them, `add price` wrote a second
quote for a day that already had one, and `--allow-errors` called an error
already in the books new.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app
from tests.test_price import _run_bea
from tests.test_price import feed_server as feed_server

runner = CliRunner()

LAYOUTS = {"dotdot": ("books/2026", "../shared/prices.bean"), "plain": ("books", "shared/prices.bean")}

MANAGED_ROOT = """\
option "operating_currency" "USD"
2026-01-01 open Assets:Bank USD
include "{include}"
include "{feed}/prices/BTC-USD"
"""
EUR_PRICE = "2026-01-03 price EUR 1.10 USD\n"


@pytest.fixture(params=sorted(LAYOUTS))
def managed_books(request: pytest.FixtureRequest, tmp_path: Path, feed_server: str) -> tuple[Path, Path]:
    root_dir, include = LAYOUTS[request.param]
    (tmp_path / "books" / "shared").mkdir(parents=True)
    (tmp_path / root_dir).mkdir(exist_ok=True)
    root = tmp_path / root_dir / "main.bean"
    root.write_text(MANAGED_ROOT.format(include=include, feed=feed_server))
    shared = tmp_path / "books" / "shared" / "prices.bean"
    shared.write_text(EUR_PRICE)
    return root, shared


def _managed(
    tmp_path: Path, feed_server: str, root: Path, *args: str, offline: bool = False
) -> subprocess.CompletedProcess[str]:
    mode = ["--offline"] if offline else []
    result = _run_bea(tmp_path, feed_server, *mode, "--file", str(root), *args)
    assert ".bea-" not in result.stdout + result.stderr, result.stdout + result.stderr
    return result


def _price_rows(result: subprocess.CompletedProcess[str]) -> dict[str, bool]:
    assert result.returncode == 0, result.stderr
    return {f"{row['date']} {row['currency']}": bool(row.get("generated")) for row in json.loads(result.stdout)["data"]}


@pytest.mark.parametrize("offline", [False, True], ids=["online", "offline"])
def test_the_included_price_lists_as_written_beside_a_managed_include(
    managed_books: tuple[Path, Path], tmp_path: Path, feed_server: str, offline: bool
) -> None:
    root, _ = managed_books
    # The offline load reads the revision this one caches.
    assert _managed(tmp_path, feed_server, root, "check").returncode == 0

    everything = _price_rows(_managed(tmp_path, feed_server, root, "--json", "list", "price", offline=offline))
    on_disk = _price_rows(
        _managed(tmp_path, feed_server, root, "--json", "list", "price", "--on-disk", offline=offline)
    )

    assert everything == {"2026-01-03 EUR": False, "2026-09-10 BTC": True, "2026-09-11 BTC": True}
    assert on_disk == {"2026-01-03 EUR": False}


@pytest.mark.parametrize("offline", [False, True], ids=["online", "offline"])
def test_a_second_quote_is_refused_beside_a_managed_include(
    managed_books: tuple[Path, Path], tmp_path: Path, feed_server: str, offline: bool
) -> None:
    root, shared = managed_books
    before = root.read_text()
    assert _managed(tmp_path, feed_server, root, "check").returncode == 0

    result = _managed(
        tmp_path,
        feed_server,
        root,
        "add",
        "price",
        "--commodity",
        "EUR",
        "--amount",
        "1.25 USD",
        "--date",
        "2026-01-03",
        offline=offline,
    )

    assert result.returncode == 4, result.stdout + result.stderr
    flat = " ".join(result.stderr.split())
    assert f"EUR already has a 2026-01-03 price of 1.10 USD (at {shared}:1); refusing 1.25 USD" in flat
    assert root.read_text() == before
    assert shared.read_text() == EUR_PRICE


def test_a_query_names_the_included_file_beside_a_managed_include(
    managed_books: tuple[Path, Path], tmp_path: Path, feed_server: str
) -> None:
    root, shared = managed_books

    result = _managed(
        tmp_path, feed_server, root, "--json", "query", "SELECT meta['filename'] FROM #prices WHERE currency = 'EUR'"
    )

    assert result.returncode == 0, result.stderr
    assert str(shared) in result.stdout


NEW_FILE_ROOT = """\
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
HOOL_PRICES = "2026-01-01 commodity HOOL\n2026-02-10 price HOOL 110.00 USD\n"
FAILING_BALANCE = "2026-01-24 balance Assets:Checking  5.00 USD\n"
NEW_FILE_LAYOUTS = {"dotdot": "../shared/prices.bean", "plain": "shared/prices.bean"}


@pytest.fixture(params=sorted(NEW_FILE_LAYOUTS))
def period_books(request: pytest.FixtureRequest, tmp_path: Path) -> tuple[Path, Path]:
    include = NEW_FILE_LAYOUTS[request.param]
    books = tmp_path / "books"
    (books / "2026").mkdir(parents=True)
    root = books / "main.bean"
    root.write_text(NEW_FILE_ROOT.format(include=include))
    (books / "2026" / "01.bean").write_text('2026-01-03 event "location" "NYC"\n')
    shared = (books / include).resolve()
    shared.parent.mkdir(exist_ok=True)
    shared.write_text(HOOL_PRICES)
    return root, shared


def _add(root: Path, *args: str) -> Any:
    result = runner.invoke(app, ["--file", str(root), *args, "--into", "2026/02.bean"])
    assert ".bea-" not in result.output, result.output
    return result


def test_a_different_quote_into_a_new_period_file_is_refused(period_books: tuple[Path, Path]) -> None:
    root, shared = period_books

    result = _add(root, "add", "price", "--date", "2026-02-10", "-c", "HOOL", "--amount", "111 USD")

    assert result.exit_code == 4, result.output
    flat = " ".join(result.output.split())
    assert f"HOOL already has a 2026-02-10 price of 110.00 USD (at {shared}:2); refusing 111 USD" in flat
    assert not (root.parent / "2026" / "02.bean").exists()


def test_the_same_quote_into_a_new_period_file_is_a_duplicate(period_books: tuple[Path, Path]) -> None:
    root, shared = period_books

    result = _add(root, "--json", "add", "price", "--date", "2026-02-10", "-c", "HOOL", "--amount", "110.00 USD")

    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)["data"]
    assert (data["written"], data["duplicate"]) == (0, True)
    assert data["source"] == {"filename": str(shared), "lineno": 2}
    assert not (root.parent / "2026" / "02.bean").exists()


def test_allow_errors_into_a_new_period_file_tolerates_the_old_error(period_books: tuple[Path, Path]) -> None:
    root, shared = period_books
    shared.write_text(HOOL_PRICES + FAILING_BALANCE)

    result = _add(
        root, "add", "note", "--date", "2026-03-01", "-a", "Assets:Checking", "-m", "new month", "--allow-errors"
    )

    assert result.exit_code == 0, result.output
    assert f"{shared}:3: Balance failed for 'Assets:Checking'" in " ".join(result.output.split())
    assert '2026-03-01 note Assets:Checking "new month"' in (root.parent / "2026" / "02.bean").read_text()
