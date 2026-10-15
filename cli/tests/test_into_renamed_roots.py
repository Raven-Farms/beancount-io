"""`--into` on a ledger with renamed roots explains or seeds the per-file options (w5/462).

Beancount applies `option "name_*"` per file while parsing, so an include
reads the default roots. Every `--into` write naming a renamed root was
refused with a bare `Invalid account name`, and a new glob member could
never take one.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RENAMED = """option "name_assets" "Aktiva"
option "name_expenses" "Aufwand"
option "name_equity" "Eigenkapital"
option "operating_currency" "USD"
include "sub.bean"
include "glob/*.bean"
2026-01-01 open Aktiva:Cash USD
2026-01-01 open Aufwand:Food USD
"""
SEED = 'option "name_assets" "Aktiva"\noption "name_expenses" "Aufwand"\noption "name_equity" "Eigenkapital"\n'


def _books(tmp_path: Path, main: str) -> Path:
    (tmp_path / "main.bean").write_text(main)
    (tmp_path / "sub.bean").write_text("")
    (tmp_path / "glob").mkdir()
    # The glob already matches one member, so the ledger loads cleanly.
    (tmp_path / "glob" / "old.bean").write_text(SEED if "Aktiva" in main else "")
    return tmp_path


def _add(books: Path, into: str, *postings: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    args = ["-f", str(books / "main.bean"), "add", "transaction", "X", "--date", "2026-01-05"]
    for posting in postings:
        args += ["-p", posting]
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args, "--into", into],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def test_an_existing_include_is_refused_with_the_per_file_hint(tmp_path: Path) -> None:
    books = _books(tmp_path, RENAMED)
    result = _add(books, "sub.bean", "Aufwand:Food 5 USD", "Aktiva:Cash")
    assert result.returncode == 1, result.stderr
    assert "Invalid account name: Aufwand:Food" in result.stderr
    hint = 'Beancount applies option "name_*" per file, so sub.bean reads the default roots.'
    assert result.stderr.count(hint) == 1
    assert 'option "name_assets" "Aktiva"' in result.stderr
    assert (books / "sub.bean").read_text() == ""


def test_a_new_glob_member_starts_with_the_roots_options(tmp_path: Path) -> None:
    books = _books(tmp_path, RENAMED)
    result = _add(books, "glob/new.bean", "Aufwand:Food 5 USD", "Aktiva:Cash")
    assert result.returncode == 0, result.stderr
    written = (books / "glob" / "new.bean").read_text()
    assert written.startswith(SEED)
    assert '2026-01-05 * "X"' in written


def test_a_default_root_ledger_gets_no_seed(tmp_path: Path) -> None:
    main = 'option "operating_currency" "USD"\ninclude "glob/*.bean"\n'
    main += "2026-01-01 open Assets:Cash USD\n2026-01-01 open Expenses:Food USD\n"
    books = _books(tmp_path, main)
    result = _add(books, "glob/new.bean", "Expenses:Food 5 USD", "Assets:Cash")
    assert result.returncode == 0, result.stderr
    assert (books / "glob" / "new.bean").read_text().lstrip().startswith('2026-01-05 * "X"')
