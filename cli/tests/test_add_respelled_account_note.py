"""A write that respells an account for other Beancount tools says so (w5/199).

`bea` reads the NFC and NFD spellings of one account name as one account and
writes new directives NFC. Stock Beancount compares code points, so on a
ledger spelled NFD the new line names an account nobody opened: a file
`bean-check` passed before an exit-0 `bea add` failed after it, silently.
The write is unchanged; it now carries a note naming both spellings.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

NFC = unicodedata.normalize("NFC", "Assets:Café")
NFD = unicodedata.normalize("NFD", "Assets:Café")
NOTE = "other Beancount tools such as bean-check read two"


def _bea(tmp_path: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--file", str(tmp_path / "main.bean"), *args],
        env=env,
        cwd=tmp_path,
        input=stdin,
        stdin=subprocess.DEVNULL if stdin is None else None,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _ledger(tmp_path: Path, account: str) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(
        f"2026-01-01 open {account} USD\n"
        "2026-01-01 open Equity:Opening\n\n"
        '2026-01-02 * "o"\n'
        f"  {account}  5 USD\n"
        "  Equity:Opening\n",
        encoding="utf-8",
    )
    return path


def _stock_errors(path: Path) -> str:
    """What stock `bean-check` prints, in an interpreter clear of the helper's NFC reading."""
    result = subprocess.run(
        [sys.executable, "-c", "from beancount.scripts.check import main; main()", str(path)],
        env={k: v for k, v in os.environ.items() if k != "PYTHONPATH"},
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert (result.returncode == 0) == (result.stderr == ""), result.stderr
    return result.stderr


def test_add_on_an_nfd_ledger_notes_the_spelling_other_tools_reject(tmp_path: Path) -> None:
    path = _ledger(tmp_path, NFD)
    assert _stock_errors(path) == ""

    result = _bea(tmp_path, "add", "note", "--date", "2026-02-01", "-a", NFD, "-m", "hi")

    assert result.returncode == 0, result.stderr
    assert "Added 1 note" in result.stdout
    # The documented write: NFC for the new line, existing bytes untouched.
    assert path.read_text(encoding="utf-8").splitlines()[-1] == f'2026-02-01 note {NFC} "hi"'
    assert path.read_text(encoding="utf-8").count(NFD) == 2
    # The consequence the note is about is real for stock Beancount ...
    assert "unknown account" in _stock_errors(path)
    # ... and is no longer silent: both spellings, as escapes, on stderr.
    assert NOTE in result.stderr
    assert ascii(NFC) in result.stderr and "(NFC)" in result.stderr
    assert ascii(NFD) in result.stderr and "(NFD)" in result.stderr
    assert "Re-save the ledger in Unicode NFC" in result.stderr
    assert NOTE not in result.stdout


def test_json_add_carries_the_note_as_a_warning(tmp_path: Path) -> None:
    _ledger(tmp_path, NFD)

    result = _bea(tmp_path, "--json", "add", "note", "--date", "2026-02-01", "-a", NFC, "-m", "hi")

    assert result.returncode == 0, result.stderr
    warnings = json.loads(result.stdout)["data"]["warnings"]
    assert len(warnings) == 1
    assert NOTE in warnings[0] and ascii(NFD) in warnings[0]


def test_every_respelling_write_is_noted_not_only_the_first(tmp_path: Path) -> None:
    _ledger(tmp_path, NFD)
    first = _bea(tmp_path, "add", "note", "--date", "2026-02-01", "-a", NFD, "-m", "one")
    second = _bea(tmp_path, "add", "note", "--date", "2026-02-02", "-a", NFD, "-m", "two")

    assert (first.returncode, second.returncode) == (0, 0)
    assert NOTE in first.stderr
    assert NOTE in second.stderr


def test_transaction_and_bulk_rows_are_noted_once_per_account(tmp_path: Path) -> None:
    _ledger(tmp_path, NFD)

    single = _bea(
        tmp_path, "add", "transaction", "--date", "2026-02-03", "-n", "t",
        "-p", f"{NFD} 1 USD", "-p", "Equity:Opening",
    )  # fmt: skip
    assert single.returncode == 0, single.stderr
    assert single.stderr.count(NOTE) == 1

    rows = [
        {
            "date": f"2026-02-0{day}",
            "narration": "b",
            "postings": [{"account": NFD, "amount": "1 USD"}, {"account": "Equity:Opening"}],
        }
        for day in (4, 5)
    ]
    bulk = _bea(tmp_path, "add", "transactions", "--from", "-", stdin=json.dumps(rows))
    assert bulk.returncode == 0, bulk.stderr
    assert bulk.stderr.count(NOTE) == 1


@pytest.mark.parametrize("typed", [NFC, NFD], ids=["typed-nfc", "typed-nfd"])
def test_an_nfc_ledger_stays_valid_for_stock_beancount_without_a_note(tmp_path: Path, typed: str) -> None:
    path = _ledger(tmp_path, NFC)

    result = _bea(tmp_path, "add", "note", "--date", "2026-02-01", "-a", typed, "-m", "hi")

    assert result.returncode == 0, result.stderr
    assert NOTE not in result.stderr
    assert _stock_errors(path) == ""


def test_the_name_inside_a_string_or_comment_is_not_an_account(tmp_path: Path) -> None:
    path = _ledger(tmp_path, NFC)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f'; was {NFD}\n2026-01-03 note Equity:Opening "{NFD}"\n')

    result = _bea(tmp_path, "add", "note", "--date", "2026-02-01", "-a", NFC, "-m", f"moved from {NFD}")

    assert result.returncode == 0, result.stderr
    assert NOTE not in result.stderr
    assert _stock_errors(path) == ""
