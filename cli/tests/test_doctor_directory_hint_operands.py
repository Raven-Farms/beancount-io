"""`bea doctor OP DIR …` suggests a command that keeps every other operand (w5/344).

The directory hint kept only the ledger: `context DIR 3` suggested
`context DIR/main.bean`, which upstream refused for its missing LOCATION.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n2026-01-01 open Equity:Opening\n'


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


@pytest.mark.parametrize("op", ["context", "region", "linked"])
def test_the_hint_keeps_the_other_operands(tmp_path: Path, op: str) -> None:
    books = tmp_path / "my books"
    books.mkdir()
    (books / "main.bean").write_text(LEDGER)
    result = _bea(tmp_path, "doctor", op, str(books), "3")
    assert result.returncode == 2
    message = " ".join(result.stderr.split())
    expected = shlex.join(["bea", "doctor", op, str(books / "main.bean"), "3"])
    assert f"for example {expected}." in message


def test_the_pasted_context_hint_runs(tmp_path: Path) -> None:
    books = tmp_path / "my books"
    books.mkdir()
    (books / "main.bean").write_text(LEDGER)
    hint = " ".join(_bea(tmp_path, "doctor", "context", str(books), "3").stderr.split()).split("for example ", 1)[1]
    argv = shlex.split(hint.rstrip("."))
    assert argv[:3] == ["bea", "doctor", "context"]
    assert _bea(tmp_path, *argv[1:]).returncode == 0
