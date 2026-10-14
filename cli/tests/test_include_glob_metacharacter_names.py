"""An included file named with `[…]`, `*` or `?` still takes writes and exports (w5/247).

`bea` writes the files an include matched back as literal `include` lines —
for the staged copy a write validates, and for the tree `price export`
produces — and Beancount globs every include string again. `2024 [old].bean`
therefore read as a character class matching nothing: every `add` and
`import --apply` failed on a ledger `bean-check` accepts, and the export
exited 0 with a copy that does not load.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from tests.test_price import _run_bea
from tests.test_price import feed_server as feed_server

ROOT = Path(__file__).resolve().parents[1]

OPENS = "2026-01-01 open Assets:Checking USD\n2026-01-01 open Expenses:Food USD\n"
CSV = "Date,Description,Amount\n2026-03-03,Coffee,-4.50\n"
# What a file system may refuse in a name differs by platform; `[` is legal everywhere.
POSIX_ONLY = pytest.mark.skipif(sys.platform == "win32", reason="`*` and `?` are not legal in Windows file names")


def _tx(payee: str) -> str:
    return f'2026-02-07 * "{payee}"\n  Expenses:Food  1.00 USD\n  Assets:Checking\n'


def _bracketed_file(books: Path) -> str:
    (books / "inc").mkdir()
    (books / "inc" / "2024 [old].bean").write_text(_tx("Extra"), encoding="utf-8")
    return 'include "inc/*.bean"\n'


def _bracketed_folder(books: Path) -> str:
    (books / "years" / "2024 [old]").mkdir(parents=True)
    (books / "years" / "2024 [old]" / "tx.bean").write_text(_tx("Extra"), encoding="utf-8")
    return 'include "years/*/*.bean"\n'


def _escaped_literal_include(books: Path) -> str:
    (books / "inc").mkdir()
    (books / "inc" / "2024 [old].bean").write_text(_tx("Extra"), encoding="utf-8")
    return 'include "inc/2024 [[]old].bean"\n'


def _question_mark_beside_its_match(books: Path) -> str:
    (books / "inc").mkdir()
    (books / "inc" / "q?.bean").write_text(_tx("Wildcard"), encoding="utf-8")
    (books / "inc" / "q2.bean").write_text(_tx("Second"), encoding="utf-8")
    return 'include "inc/*.bean"\n'


def _star_beside_its_match(books: Path) -> str:
    (books / "inc").mkdir()
    (books / "inc" / "a*.bean").write_text(_tx("Wildcard"), encoding="utf-8")
    (books / "inc" / "ab.bean").write_text(_tx("Second"), encoding="utf-8")
    return 'include "inc/*.bean"\n'


def _plain_name(books: Path) -> str:
    (books / "inc").mkdir()
    (books / "inc" / "2024 old.bean").write_text(_tx("Extra"), encoding="utf-8")
    return 'include "inc/*.bean"\n'


LAYOUTS = [
    pytest.param(_bracketed_file, id="bracketed-file"),
    pytest.param(_bracketed_folder, id="bracketed-folder"),
    pytest.param(_escaped_literal_include, id="escaped-literal-include"),
    pytest.param(_question_mark_beside_its_match, id="question-mark-beside-match", marks=POSIX_ONLY),
    pytest.param(_star_beside_its_match, id="star-beside-match", marks=POSIX_ONLY),
    pytest.param(_plain_name, id="plain-name-control"),
]


def _books(tmp_path: Path, arrange: Callable[[Path], str]) -> Path:
    books = tmp_path / "books"
    books.mkdir()
    (books / "main.bean").write_text('option "operating_currency" "USD"\n' + arrange(books) + OPENS, encoding="utf-8")
    (books / "bank.csv").write_text(CSV, encoding="utf-8")
    return books


def _bea(tmp_path: Path, books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--file", "main.bean", *args],
        env=env,
        cwd=books,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _stock_check(ledger: Path) -> subprocess.CompletedProcess[str]:
    """Stock `bean-check`, which knows nothing of how `bea` staged or exported the files."""
    return subprocess.run(
        [sys.executable, "-m", "beancount.scripts.check", str(ledger)],
        cwd=ledger.parent,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _files(books: Path) -> dict[str, bytes]:
    return {str(path.relative_to(books)): path.read_bytes() for path in sorted(books.rglob("*")) if path.is_file()}


def _add_lunch(tmp_path: Path, books: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return _bea(
        tmp_path,
        books,
        "add",
        "transaction",
        "Lunch",
        "--date",
        "2026-03-01",
        "-p",
        "Expenses:Food 7.00 USD",
        "-p",
        "Assets:Checking",
        *extra,
    )


@pytest.mark.parametrize("arrange", LAYOUTS)
def test_add_and_import_write_only_the_root(tmp_path: Path, arrange: Callable[[Path], str]) -> None:
    books = _books(tmp_path, arrange)
    assert _stock_check(books / "main.bean").returncode == 0
    before = _files(books)

    added = _add_lunch(tmp_path, books)
    assert added.returncode == 0, added.stderr or added.stdout
    imported = _bea(
        tmp_path,
        books,
        "import",
        "bank.csv",
        "--account",
        "Assets:Checking",
        "--default-account",
        "Expenses:Food",
        "--apply",
    )
    assert imported.returncode == 0, imported.stderr or imported.stdout

    after = _files(books)
    assert {name for name in after if after[name] != before.get(name)} == {"main.bean"}
    root = after["main.bean"].decode("utf-8")
    assert root.startswith(before["main.bean"].decode("utf-8"))
    assert '"Lunch"' in root and '"Coffee"' in root
    stock = _stock_check(books / "main.bean")
    assert stock.returncode == 0, stock.stderr


@pytest.mark.parametrize("arrange", LAYOUTS)
def test_price_export_writes_a_copy_stock_beancount_loads(tmp_path: Path, arrange: Callable[[Path], str]) -> None:
    books = _books(tmp_path, arrange)
    postings = "SELECT count(*) AS postings"
    source = _bea(tmp_path, books, "--json", "query", postings)
    assert source.returncode == 0, source.stderr
    assert json.loads(source.stdout)["data"]["rows"][0][0] > 0

    output = tmp_path / "exp"
    exported = _bea(tmp_path, books, "--offline", "price", "export", "-o", str(output))
    assert exported.returncode == 0, exported.stderr or exported.stdout

    stock = _stock_check(output / "main.bean")
    assert stock.returncode == 0, stock.stderr
    # Nothing was folded into a neighbour or read twice on the way.
    copy = _bea(tmp_path, output, "--json", "query", postings)
    assert copy.returncode == 0, copy.stderr
    assert json.loads(copy.stdout)["data"]["rows"] == json.loads(source.stdout)["data"]["rows"]


def test_a_bracketed_into_file_does_not_break_the_next_write(tmp_path: Path) -> None:
    books = _books(tmp_path, _plain_name)

    first = _add_lunch(tmp_path, books, "--into", "inc/new [2].bean")
    assert first.returncode == 0, first.stderr or first.stdout
    assert '"Lunch"' in (books / "inc" / "new [2].bean").read_text(encoding="utf-8")
    second = _add_lunch(tmp_path, books, "--into", "inc/new [2].bean")
    assert second.returncode == 0, second.stderr or second.stdout
    third = _add_lunch(tmp_path, books)
    assert third.returncode == 0, third.stderr or third.stdout

    assert (books / "inc" / "new [2].bean").read_text(encoding="utf-8").count('"Lunch"') == 2
    assert _stock_check(books / "main.bean").returncode == 0


def test_a_managed_price_include_reads_past_a_bracketed_file(feed_server: str, tmp_path: Path) -> None:
    """The managed loader stages the same literal includes for every read."""
    # A staged copy sits beside its source under a generated name, so it is the folder that carries the brackets.
    (tmp_path / "years" / "2024 [old]").mkdir(parents=True)
    (tmp_path / "years" / "2024 [old]" / "a.bean").write_text(_tx("Extra"), encoding="utf-8")
    (tmp_path / "years" / "2024 [old]" / "b.bean").write_text(_tx("Later"), encoding="utf-8")
    ledger = tmp_path / "main.bean"
    ledger.write_text(f'include "{feed_server}/prices/BTC-USD"\ninclude "years/*/*.bean"\n' + OPENS, encoding="utf-8")

    checked = _run_bea(tmp_path, feed_server, "--file", str(ledger), "check")
    assert checked.returncode == 0, checked.stderr or checked.stdout
    counted = _run_bea(tmp_path, feed_server, "--json", "--file", str(ledger), "query", "SELECT count(*) AS postings")
    assert counted.returncode == 0, counted.stderr
    assert json.loads(counted.stdout)["data"]["rows"] == [[4]]
