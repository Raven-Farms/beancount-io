"""A BQL usage error must end with advice that works where it is printed (w5/198).

The hint sent every caller to the interactive shell, which `--json` and a
caller without a terminal cannot open: `bea query` with no argument is a usage
error there. `bea query .tables` runs in every mode.
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
LEDGER = "2020-01-01 open Assets:Checking USD\n"
HINT = "Run bea query .tables to list what you can query."
MISTAKES = {
    "unknown column": "SELECT acount",
    "unknown table": "SELECT * FROM nope",
    "syntax error": "SELEC 1",
}


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
        timeout=30,
    )


def _follow(tmp_path: Path, hint: str) -> subprocess.CompletedProcess[str]:
    """Run the command the hint names, exactly as it spells it: ledger and mode included (w5/838)."""
    command = shlex.split(hint.removeprefix("Run ").split(" to list ")[0])
    assert command[0] == "bea"
    return _bea(tmp_path, *command[1:])


@pytest.mark.parametrize("query", MISTAKES.values(), ids=MISTAKES.keys())
def test_json_error_hint_names_a_command_that_runs(tmp_path: Path, query: str) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)

    failed = _bea(tmp_path, "--json", "-f", "main.bean", "query", query)
    assert failed.returncode == 2, failed.stderr
    details = json.loads(failed.stderr)["error"]["details"]
    assert details[-1] == HINT.replace("Run bea ", "Run bea --json ")
    assert "interactive shell" not in failed.stderr

    followed = _follow(tmp_path, details[-1])
    assert followed.returncode == 0, followed.stderr
    assert "postings" in json.loads(followed.stdout)["data"]["text"]


@pytest.mark.parametrize("query", MISTAKES.values(), ids=MISTAKES.keys())
def test_text_error_hint_names_a_command_that_runs(tmp_path: Path, query: str) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)

    failed = _bea(tmp_path, "-f", "main.bean", "query", query)
    assert failed.returncode == 2, failed.stderr
    last = failed.stderr.rstrip().splitlines()[-1].strip()
    assert last == HINT
    assert "interactive shell" not in failed.stderr

    followed = _follow(tmp_path, last)
    assert followed.returncode == 0, followed.stderr
    assert "postings" in followed.stdout.split()


def test_the_shell_the_old_hint_named_is_refused_without_a_terminal(tmp_path: Path) -> None:
    """Why the hint cannot name the shell: no argument and no terminal is exit 2."""
    (tmp_path / "main.bean").write_text(LEDGER)
    for leading in (("--json",), ()):
        result = _bea(tmp_path, *leading, "-f", "main.bean", "query")
        assert result.returncode == 2, (leading, result.stderr)
        assert "A query is required" in result.stderr
