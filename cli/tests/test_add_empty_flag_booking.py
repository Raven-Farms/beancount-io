"""An empty `--flag` or `--booking` is refused, not read as omitted (w5/382).

w5/239 set the rule for other options; these two still fell back: `--flag ''`
wrote a cleared `*` transaction (bulk add refused the same empty flag) and
`--booking ' '` wrote an open with no booking method.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Expenses:Food USD\n2026-01-01 open Assets:Cash USD\n'
TRANSACTION = ("add", "transaction", "X", "--date", "2026-01-02", "-p", "Expenses:Food 1 USD", "-p", "Assets:Cash")


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
        [sys.executable, "-m", "cli.main", "-f", "main.bean", *args],
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
        ((*TRANSACTION, "--flag", ""), "--flag: '' is not a flag"),
        (
            ("add", "open", "--account", "Assets:Bank", "--date", "2026-01-01", "--booking", " "),
            "--booking ' ' is blank",
        ),
        (("add", "open", "--account", "Assets:Bank", "--date", "2026-01-01", "--booking", ""), "--booking '' is blank"),
    ],
    ids=["empty-flag", "blank-booking", "empty-booking"],
)
@pytest.mark.parametrize("json_mode", [False, True], ids=["text", "json"])
def test_an_empty_value_is_refused_naming_the_option(
    tmp_path: Path, args: tuple[str, ...], named: str, json_mode: bool
) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)

    result = _bea(tmp_path, *(["--json"] if json_mode else []), *args)

    assert result.returncode == 2, result.stdout + result.stderr
    if json_mode:
        error = json.loads(result.stderr)["error"]
        text = " ".join([error["message"], *error.get("details", [])])
    else:
        text = result.stderr
    assert named in text
    assert ledger.read_text() == LEDGER


def test_an_omitted_flag_still_writes_a_cleared_transaction(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)

    result = _bea(tmp_path, *TRANSACTION)

    assert result.returncode == 0, result.stderr
    assert '2026-01-02 * "X"' in ledger.read_text()
