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
