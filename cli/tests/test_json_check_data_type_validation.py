"""`--json check` and the helper's text check run bean-check's data-type validation (w5/493).

The helper computed `HARDCORE_VALIDATIONS` only for `--documents-only`, so a
plugin's malformed entries failed text `check` and passed `--json check`
with `valid: true`, the verdict scripts gate on. A BOM-marked ledger, which
text `check` sends through the helper, passed too.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = """from beancount.core import data
__plugins__ = ['notags']
def notags(entries, options_map):
    return [e._replace(tags=None) if isinstance(e, data.Transaction) else e for e in entries], []
"""
LEDGER = """option "insert_pythonpath" "TRUE"
plugin "notags"
2024-01-01 open Assets:Cash USD
2024-01-01 open Expenses:Food USD
2024-01-05 * "Lunch"
  Expenses:Food    10 USD
  Assets:Cash
"""


def _check(tmp_path: Path, ledger: bytes, *flags: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "notags.py").write_text(PLUGIN)
    (tmp_path / "main.bean").write_bytes(ledger)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *flags, "-f", str(tmp_path / "main.bean"), "check"],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_json_check_fails_on_invalid_data_types(tmp_path: Path) -> None:
    result = _check(tmp_path, LEDGER.encode(), "--json")

    assert result.returncode == 1, result.stdout + result.stderr
    error = json.loads(result.stdout or result.stderr)["error"]
    assert any(
        detail.endswith("main.bean:5: Invalid data types: Invalid tags type: <class 'NoneType'>")
        for detail in error["details"]
    )


@pytest.mark.parametrize("flags", [(), ("--json",)], ids=["text", "json"])
def test_a_bom_marked_ledger_fails_too(tmp_path: Path, flags: tuple[str, ...]) -> None:
    result = _check(tmp_path, b"\xef\xbb\xbf" + LEDGER.encode(), *flags)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Invalid data types" in result.stdout + result.stderr


def test_a_valid_ledger_still_passes_in_json(tmp_path: Path) -> None:
    result = _check(tmp_path, LEDGER.replace('plugin "notags"\n', "").encode(), "--json")

    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["data"]["valid"] is True
