"""The unknown-account and missing-commodity remedies name the ledger they are about (w5/619).

`To create it, use bea add open …` and `Declare it first: bea add commodity …`
dropped the `--file` the user passed. Pasted in a directory with another
`main.bean`, the open landed in that decoy with exit 0, and the original
command still failed.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n2026-01-01 open Expenses:Food USD\n'
CHECKED = (
    'option "operating_currency" "USD"\nplugin "beancount.plugins.check_commodity"\n2026-01-01 commodity USD\n'
    "2026-01-01 open Assets:Cash\n2026-01-01 open Expenses:Food\n"
)


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
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _paste(cwd: Path, stderr: str, pattern: str) -> subprocess.CompletedProcess[str]:
    found = re.search(pattern, " ".join(stderr.split()))
    assert found, stderr
    command = shlex.split(found.group(1).replace("YYYY-MM-DD", "2026-01-01"))
    assert command[:2] == ["bea", "--file"]
    return _bea(cwd, *command[1:])


@pytest.mark.parametrize(
    ("text", "posting", "pattern"),
    [
        (LEDGER, "Expenses:Coffee 4 USD", r"To create it, use (bea .*? --date YYYY-MM-DD)\."),
        (CHECKED, "Expenses:Food 4 EUR", r"Declare it first: (bea .*? --currency EUR), then retry\."),
    ],
    ids=["add-open", "add-commodity"],
)
def test_the_pasted_remedy_fixes_the_ledger_named_not_a_decoy(
    tmp_path: Path, text: str, posting: str, pattern: str
) -> None:
    (tmp_path / "books").mkdir()
    (tmp_path / "books" / "main.bean").write_text(text)
    (tmp_path / "main.bean").write_text(text)
    add = ["--file", "books/main.bean", "add", "transaction", "Latte", "--date", "2026-04-01"]
    add += ["-p", posting, "-p", "Assets:Cash"]

    refused = _bea(tmp_path, *add)
    assert refused.returncode == 1, refused.stderr

    pasted = _paste(tmp_path, refused.stderr, pattern)
    assert pasted.returncode == 0, pasted.stderr
    assert (tmp_path / "main.bean").read_text() == text
    assert _bea(tmp_path, *add).returncode == 0
