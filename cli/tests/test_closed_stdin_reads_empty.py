"""With stdin closed (`<&-`), commands read it as empty input (w5/584).

Python leaves `sys.stdin` None then: `query`, `format -` and `add transactions
--from -` exited 1 with `'NoneType' object has no attribute 'isatty'` or
`'read'`, and treeify's child started with no fd 0. A closed stdin now
behaves as `</dev/null` does.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="closes a POSIX descriptor")

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("args", "code", "says"),
    [
        (["query"], 2, "A query is required as an argument or on stdin."),
        (["query", "--source", "main.bean"], 2, "A query is required as an argument or on stdin."),
        (["format", "-"], 0, ""),
        (["add", "transactions", "--from", "-"], 2, "Invalid JSON at line 1"),
        (["treeify"], 2, "treeify found no hierarchical column"),
    ],
    ids=["query", "query-source", "format", "add-transactions", "treeify"],
)
def test_a_closed_stdin_reads_as_empty(tmp_path: Path, args: list[str], code: int, says: str) -> None:
    (tmp_path / "main.bean").write_text('option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n')
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )

    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        # `<&-`: the child starts with no descriptor 0 at all.
        preexec_fn=lambda: os.close(0),  # noqa: PLW1509 - no threads started yet
        timeout=120,
    )

    assert result.returncode == code, result.stdout + result.stderr
    assert says in result.stderr
    assert "NoneType" not in result.stdout + result.stderr
