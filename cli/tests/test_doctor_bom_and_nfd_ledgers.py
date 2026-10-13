"""`bea doctor` reads a BOM-marked or NFD ledger as `bea check` does (w5/135).

The forwarded operations ran stock `bean-doctor`, which lexes the mark as an
error token and keeps NFC and NFD spellings of one account apart. On a ledger
`bea check` called valid, `print-options` printed default options and
`missing-open` proposed an `open` for an account already open, both exit 0.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BOM = b"\xef\xbb\xbf"
OPTION = 'option "operating_currency" "EUR"\n'
BOOKS = """2026-01-01 open Assets:Cash
2026-01-01 open Equity:Opening
2026-01-02 * "x"
  Assets:Cash  10.00 EUR
  Equity:Opening
"""
# The `open` precomposed, the posting decomposed: one account, two spellings.
NFD_POSTING = BOOKS.replace("open Assets:Cash", "open Expenses:Café").replace("  Assets:Cash", "  Expenses:Café")


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _write(tmp_path: Path, name: str, text: str, *, bom: bool = False) -> Path:
    books = tmp_path / "books"
    books.mkdir(exist_ok=True)
    ledger = books / name
    ledger.write_bytes((BOM if bom else b"") + text.encode("utf-8"))
    return ledger


def _bom_root(tmp_path: Path) -> Path:
    return _write(tmp_path, "main.bean", BOOKS, bom=True)


def _bom_include(tmp_path: Path) -> Path:
    _write(tmp_path, "inc.bean", BOOKS, bom=True)
    return _write(tmp_path, "main.bean", 'include "inc.bean"\n')


def _nfd_posting(tmp_path: Path) -> Path:
    return _write(tmp_path, "main.bean", NFD_POSTING)


SHAPES = pytest.mark.parametrize("shape", [_bom_root, _bom_include, _nfd_posting])


def _ran(result: subprocess.CompletedProcess[str]) -> str:
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def _option(stdout: str, name: str) -> str:
    return next(line for line in stdout.splitlines() if line.startswith(f"{name}:"))


@SHAPES
def test_missing_open_proposes_nothing_for_an_account_that_is_open(
    tmp_path: Path, shape: Callable[[Path], Path]
) -> None:
    ledger = shape(tmp_path)
    assert _bea(tmp_path, "-f", str(ledger), "check").returncode == 0
    assert _ran(_bea(tmp_path, "doctor", "missing-open", str(ledger))).strip() == ""


def test_missing_open_still_reports_an_account_that_is_not_open(tmp_path: Path) -> None:
    ledger = _write(tmp_path, "main.bean", BOOKS.replace("2026-01-01 open Equity:Opening\n", ""), bom=True)
    proposed = _ran(_bea(tmp_path, "doctor", "missing-open", str(ledger)))
    assert proposed.split() == ["2026-01-02", "open", "Equity:Opening"]


@pytest.mark.parametrize("include", [False, True])
def test_print_options_shows_the_options_behind_the_mark(tmp_path: Path, include: bool) -> None:
    if include:
        _write(tmp_path, "inc.bean", OPTION + BOOKS, bom=True)
        marked = _write(tmp_path, "main.bean", 'include "inc.bean"\n')
    else:
        marked = _write(tmp_path, "main.bean", OPTION + BOOKS, bom=True)
    plain = _write(tmp_path, "plain.bean", OPTION + BOOKS)
    control = _option(_ran(_bea(tmp_path, "doctor", "print-options", str(plain))), "operating_currency")
    assert control == "operating_currency: ['EUR']"
    assert _option(_ran(_bea(tmp_path, "doctor", "print-options", str(marked))), "operating_currency") == control


@pytest.mark.parametrize("op", ["lex", "dump-lexer"])
def test_lex_matches_the_unmarked_file(tmp_path: Path, op: str) -> None:
    marked = _write(tmp_path, "main.bean", OPTION + BOOKS, bom=True)
    plain = _write(tmp_path, "plain.bean", OPTION + BOOKS)
    tokens = _ran(_bea(tmp_path, "doctor", op, str(marked)))
    assert tokens.splitlines()[0].split() == ["OPTION", "1", "b'option'"]
    assert tokens == _ran(_bea(tmp_path, "doctor", op, str(plain)))


def test_lex_of_an_nfd_name_only_in_prose_keeps_the_file_s_bytes(tmp_path: Path) -> None:
    """Control: prose cannot split an account, so upstream still reads it byte for byte."""
    ledger = _write(tmp_path, "main.bean", BOOKS.replace('"x"', '"Café"'))
    assert "Cafe\\xcc\\x81" in _ran(_bea(tmp_path, "doctor", "lex", str(ledger)))


def test_parse_reads_past_the_mark(tmp_path: Path) -> None:
    result = _bea(tmp_path, "doctor", "parse", str(_bom_root(tmp_path)))
    assert result.returncode == 0, result.stderr[-2000:]
    assert "Starting parse" in result.stderr
    assert "token error" not in result.stderr


@SHAPES
def test_roundtrip_compares_the_real_entries(tmp_path: Path, shape: Callable[[Path], Path]) -> None:
    ledger = shape(tmp_path)
    result = _bea(tmp_path, "doctor", "roundtrip", str(ledger))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Entries are the same" in result.stderr
    # Upstream recovered from the mark, dropped the opens, and compared what was left.
    assert "Invalid" not in result.stdout + result.stderr
    assert sorted(path.name for path in ledger.parent.iterdir() if "roundtrip" in path.name) == []


def test_context_finds_the_entry_right_behind_the_mark(tmp_path: Path) -> None:
    opens, _, entry = BOOKS.partition("2026-01-02")
    _write(tmp_path, "inc.bean", "2026-01-02" + entry, bom=True)
    ledger = _write(tmp_path, "main.bean", opens + 'include "inc.bean"\n')
    stdout = _ran(_bea(tmp_path, "doctor", "context", str(ledger), "inc.bean:1"))
    assert f"Location: {ledger.parent / 'inc.bean'}:1" in stdout


def test_display_context_and_directories_load_the_marked_ledger(tmp_path: Path) -> None:
    # The first directive is the one upstream loses to the mark.
    ledger = _write(tmp_path, "main.bean", "2026-01-01 open Assets:Unused\n" + BOOKS, bom=True)
    assert "EUR" in _ran(_bea(tmp_path, "doctor", "display-context", str(ledger)))
    (ledger.parent / "docs" / "Assets" / "Unused").mkdir(parents=True)
    _ran(_bea(tmp_path, "doctor", "directories", str(ledger), str(ledger.parent / "docs")))
    (ledger.parent / "docs" / "Assets" / "Nowhere").mkdir()
    refused = _bea(tmp_path, "doctor", "directories", str(ledger), str(ledger.parent / "docs"))
    assert refused.returncode == 1
    assert "Nowhere" in refused.stdout + refused.stderr
