"""A `list` filter value that can never be one token is refused, as `add` refuses it (w5/340).

`--tag 'trip,work'`, `--tag '#trip#work'`, `--link 'inv-1,inv-2'`, `--flag x`
and `-c 'USD,EUR'` answered "No transactions found." with exit 0, so a script
could not tell "no such rows" from a malformed filter.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD
2026-01-05 * "Diner" "dinner" #trip #work ^inv-1
  Expenses:Food  12.00 USD
  Assets:Cash
2026-01-06 price EUR 1.1 USD
"""


def _list(tmp_path: Path, *list_args: str, json_mode: bool = False) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    flags = ["--json"] if json_mode else []
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *flags, "-f", "main.bean", "list", *list_args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize(
    ("args", "named"),
    [
        (("transaction", "--tag", "trip,work"), "--tag: 'trip,work' is not one tag or link"),
        (("transaction", "--tag", "trip work"), "--tag: 'trip work' is not one tag or link"),
        (("transaction", "--tag", "#trip#work"), "--tag: '#trip#work' is not one tag or link"),
        (("transaction", "--link", "inv-1,inv-2"), "--link: 'inv-1,inv-2' is not one tag or link"),
        (("transaction", "--flag", "x"), "--flag 'x' is not a transaction flag"),
        (("price", "-c", "USD,EUR"), "--currency: 'USD,EUR' is not one commodity"),
    ],
)
@pytest.mark.parametrize("json_mode", [False, True], ids=["text", "json"])
def test_a_non_token_filter_is_refused(tmp_path: Path, args: tuple[str, ...], named: str, json_mode: bool) -> None:
    result = _list(tmp_path, *args, json_mode=json_mode)
    assert result.returncode == 2, result.stdout + result.stderr
    message = json.loads(result.stdout or result.stderr)["error"]["message"] if json_mode else result.stderr
    assert named in message


@pytest.mark.parametrize(
    "args",
    [
        ("transaction", "--tag", "#trip"),
        ("transaction", "--tag", "trip", "--tag", "work"),
        ("transaction", "--flag", "*"),
        ("price", "-c", "eur"),
    ],
)
def test_valid_filters_still_match(tmp_path: Path, args: tuple[str, ...]) -> None:
    result = _list(tmp_path, *args)
    assert result.returncode == 0, result.stderr
    assert "No " not in result.stdout
