"""An empty path option is refused naming the option, not read as `.` (w5/386).

`Path('')` is the working directory, so `--into ''` advised creating the
ledger's own folder as an include and `--rules ''` failed as "Is a
directory". Both now say the option is empty, as w5/239 does for other
options.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = (
    'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n'
    "2026-01-01 open Expenses:Food USD\n2026-01-01 open Expenses:Uncategorized USD\n"
)
CSV = "Date,Payee,Narration,Amount\n2026-01-07,Shop,stuff,-3.00\n"
MAPPING = "date=Date,payee=Payee,narration=Narration,amount=Amount"
COMMANDS = {
    "add-into": (
        ("add", "transaction", "X", "--date", "2026-01-08", "-p", "Expenses:Food 1 USD", "-p", "Assets:Cash"),
        "--into",
    ),
    "import-into": (("import", "s.csv", "--csv", MAPPING, "--account", "Assets:Cash"), "--into"),
    "import-rules": (("import", "s.csv", "--csv", MAPPING, "--account", "Assets:Cash"), "--rules"),
}


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize("value", ["", " "], ids=["empty", "blank"])
@pytest.mark.parametrize("case", sorted(COMMANDS))
@pytest.mark.parametrize("json_mode", [False, True], ids=["text", "json"])
def test_an_empty_path_option_is_refused_naming_it(tmp_path: Path, case: str, value: str, json_mode: bool) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "s.csv").write_text(CSV)
    args, option = COMMANDS[case]

    result = _bea(tmp_path, *(["--json"] if json_mode else []), "-f", "main.bean", *args, option, value)

    assert result.returncode == 2, result.stdout + result.stderr
    message = json.loads(result.stderr)["error"]["message"] if json_mode else result.stderr
    assert f"{option} {value!r} is empty; name a path, or omit {option}." in message
    assert "include directive" not in message and "Is a directory" not in message
    assert (tmp_path / "main.bean").read_text() == LEDGER


# ── every path option and argument (w5/387) ─────────────────────────────────
#
# Typer turns `''` into `Path('')`, the working directory, so `format -i ''`
# reformatted the ledgers under the cwd and `price export -o ''` exported into
# it, both with exit 0. Each path parameter now refuses an empty value.

UNFORMATTED = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n2026-01-01 open Equity:O USD\n'
UNFORMATTED += '2026-01-02 * "x"\n  Assets:Cash      5 USD\n  Equity:O  -5 USD\n2026-01-03 price EUR 1.1 USD\n'
EVERY_PATH = {
    "format-paths": (("format", "-i", ""), "The PATHS argument is empty"),
    "price-export-output": (("-f", "books/main.bean", "price", "export", "-o", ""), "-o '' is empty"),
    "global-file": (("--file", "", "list", "transaction"), "--file '' is empty"),
    "add-from": (("-f", "books/main.bean", "add", "transactions", "--from", ""), "--from '' is empty"),
    "init-directory": (("init", "", "--currency", "USD", "--date", "2026-01-01"), "The DIRECTORY argument is empty"),
    "import-source": (("-f", "books/main.bean", "import", ""), "The SOURCE argument is empty"),
    "import-config": (("-f", "books/main.bean", "import", "x.ofx", "--config", ""), "--config '' is empty"),
    "ingest-config": (("-f", "books/main.bean", "ingest", "identify", "--config", "", "x"), "--config '' is empty"),
    "doctor-lex": (("-f", "books/main.bean", "doctor", "lex", ""), "The ledger path for bea doctor lex is empty"),
    "cloud-dir": (("cloud", "ledger", "clone", "alice/books", "--dir", ""), "--dir '' is empty"),
}


@pytest.mark.parametrize("case", sorted(EVERY_PATH))
def test_every_empty_path_is_refused_and_nothing_is_written(tmp_path: Path, case: str) -> None:
    books = tmp_path / "books"
    books.mkdir()
    (books / "main.bean").write_text(UNFORMATTED)
    args, named = EVERY_PATH[case]
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))

    result = _bea(tmp_path if not case.startswith("format") else books, *args)

    assert result.returncode == 2, result.stdout + result.stderr
    assert named in result.stderr
    assert (books / "main.bean").read_text() == UNFORMATTED
    after = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*") if "config" not in path.parts)
    assert after == [path for path in before if "config" not in path.parts]


def test_real_paths_still_work(tmp_path: Path) -> None:
    books = tmp_path / "books"
    books.mkdir()
    (books / "main.bean").write_text(UNFORMATTED)

    formatted = _bea(books, "format", "-i", "main.bean")
    exported = _bea(tmp_path, "-f", "books/main.bean", "price", "export", "-o", "out")

    assert formatted.returncode == 0, formatted.stderr
    assert (books / "main.bean").read_text() != UNFORMATTED
    assert exported.returncode == 0, exported.stderr
    assert any((tmp_path / "out").iterdir())
