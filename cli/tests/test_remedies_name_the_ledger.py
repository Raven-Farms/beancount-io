"""Printed remedies are the whole command for the same ledger and mode (w5/838).

From a directory holding `books/main.bean` and no `main.bean`, import's
"declare it first: bea add commodity …", the BQL "Run bea query .tables" /
".help" hints and `check FILE`'s "run bea --file FILE check" failed "No ledger
file" when pasted, or dropped `--json` and the check's own options.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Checking\n2026-01-01 open Expenses:Uncategorized\n'


def _bea(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(cwd / "config"),
        XDG_CACHE_HOME=str(cwd / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _pasted(cwd: Path, command: str) -> subprocess.CompletedProcess[str]:
    words = shlex.split(command)
    assert words[0] == "bea"
    return _bea(cwd, *words[1:])


@pytest.fixture
def cwd(tmp_path: Path) -> Path:
    (tmp_path / "books").mkdir()
    (tmp_path / "books" / "main.bean").write_text(LEDGER)
    (tmp_path / "eur.csv").write_text("Date,Description,Amount\n2026-03-01,Coffee,-3.50\n")
    return tmp_path


def test_the_commodity_remedy_declares_it_in_the_named_ledger(cwd: Path) -> None:
    csv = ["--csv", "date=Date,amount=Amount,narration=Description,currency=EUR", "--account", "Assets:Checking"]
    refused = _bea(cwd, "--file", "books/main.bean", "import", "eur.csv", *csv)

    assert refused.returncode == 2, refused.stderr
    said = " ".join(refused.stderr.split())
    remedy = said.split("declare it first: ", 1)[1].rstrip(".")
    assert remedy == "bea --file books/main.bean add commodity --date YYYY-MM-DD --currency EUR"
    assert _pasted(cwd, remedy.replace("YYYY-MM-DD", "2026-01-01")).returncode == 0
    assert _bea(cwd, "--file", "books/main.bean", "import", "eur.csv", *csv).returncode == 0


@pytest.mark.parametrize("mode", [(), ("--json",)], ids=["text", "json"])
@pytest.mark.parametrize(("query", "hint"), [("SELECT nope FROM postings", ".tables"), (".bogus", ".help")])
def test_the_bql_hints_name_the_ledger_and_mode(cwd: Path, mode: tuple[str, ...], query: str, hint: str) -> None:
    refused = _bea(cwd, *mode, "--file", "books/main.bean", "query", query)

    assert refused.returncode == 2, refused.stderr
    details = json.loads(refused.stderr)["error"]["details"] if mode else refused.stderr.splitlines()
    line = next(text.strip() for text in details if text.strip().startswith("Run bea"))
    command = line.removeprefix("Run ").split(f" {hint} ")[0] + f" {hint}"
    assert command == shlex.join(["bea", *mode, "--file", "books/main.bean", "query", hint])
    followed = _pasted(cwd, command)
    assert followed.returncode == 0, followed.stderr
    if mode:
        assert "text" in json.loads(followed.stdout)["data"]


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (["--json", "check", "books/main.bean"], "bea --json --file books/main.bean check"),
        (["check", "books/main.bean", "-v"], "bea --file books/main.bean check -v"),
        # `--json` takes no bean-check options, so the form that runs drops it.
        (["--json", "check", "books/main.bean", "-v"], "bea --file books/main.bean check -v"),
    ],
    ids=["json", "options", "json-with-options"],
)
def test_check_file_names_a_command_that_runs(cwd: Path, args: list[str], expected: str) -> None:
    refused = _bea(cwd, *args)

    assert refused.returncode == 2
    message = json.loads(refused.stderr)["error"]["message"] if args[0] == "--json" else refused.stderr.strip()
    assert message.split("run ", 1)[1] == expected
    followed = _pasted(cwd, expected)
    assert followed.returncode == 0, followed.stderr
    if expected.startswith("bea --json"):
        assert json.loads(followed.stdout)["data"] is not None
