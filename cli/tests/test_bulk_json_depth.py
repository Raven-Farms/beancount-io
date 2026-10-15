"""Deeply nested bulk JSON is a usage error at every depth (w5/336).

The C decoder accepts far deeper input than the engine's recursive surrogate
scan, so 1,000-3,000 levels passed the frontend's guard and died as a bare
`RecursionError` (exit 1, `validation`).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n'


def _add(tmp_path: Path, payload: str, *, stdin: bool) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
    source = "-" if stdin else "deep.json"
    if not stdin:
        (tmp_path / "deep.json").write_text(payload)
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
        [sys.executable, "-m", "cli.main", "--json", "-f", "main.bean", "add", "transactions", "--from", source],
        env=env,
        cwd=tmp_path,
        input=payload if stdin else None,
        stdin=None if stdin else subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.mark.parametrize("depth", [1_000, 3_000, 100_000])
@pytest.mark.parametrize("stdin", [False, True], ids=["file", "stdin"])
def test_deep_nesting_is_a_usage_error(tmp_path: Path, depth: int, stdin: bool) -> None:
    result = _add(tmp_path, "[" * depth + "]" * depth, stdin=stdin)
    assert result.returncode == 2, result.stderr
    error = json.loads(result.stdout or result.stderr)["error"]
    assert error["category"] == "usage" and "nests JSON too deeply" in error["message"]
    assert "RecursionError" not in result.stdout + result.stderr
    assert (tmp_path / "main.bean").read_text() == LEDGER


def test_ordinary_nesting_reaches_row_validation(tmp_path: Path) -> None:
    result = _add(tmp_path, "[" * 50 + "]" * 50, stdin=False)
    assert result.returncode == 1
    assert "failed validation" in json.loads(result.stdout or result.stderr)["error"]["message"]
