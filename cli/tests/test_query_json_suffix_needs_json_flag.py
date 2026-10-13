"""query -o out.json without --json is refused instead of writing a text table (w5/158)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD

2026-01-05 * "Café" "Lunch"
  Expenses:Food  12.00 USD
  Assets:Cash
"""
QUERY = "SELECT account, sum(position) GROUP BY account"


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        HOME=str(tmp_path / "home"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    (tmp_path / "main.bean").write_text(LEDGER, encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.parametrize("name", ["c.json", "C.JSON"])
def test_a_text_export_to_a_json_name_is_refused(tmp_path: Path, name: str) -> None:
    result = _bea(tmp_path, "-f", "main.bean", "query", QUERY, "-o", name)

    assert result.returncode == 2, result.stderr or result.stdout
    assert result.stdout == ""
    assert "looks like JSON" in result.stderr
    assert f"bea --json query … -o {name}" in result.stderr
    assert not (tmp_path / name).exists()


def test_json_export_to_a_json_name_still_writes_the_envelope(tmp_path: Path) -> None:
    result = _bea(tmp_path, "--json", "-f", "main.bean", "query", QUERY, "-o", "c.json")

    assert result.returncode == 0, result.stderr or result.stdout
    envelope = json.loads((tmp_path / "c.json").read_text(encoding="utf-8"))
    assert sorted(row[0] for row in envelope["data"]["rows"]) == ["Assets:Cash", "Expenses:Food"]


def test_an_explicit_format_still_decides_a_json_named_destination(tmp_path: Path) -> None:
    """Only the inferred default is refused; `--format` is the caller's stated choice, as for `.tsv`."""
    result = _bea(tmp_path, "-f", "main.bean", "query", QUERY, "--format", "csv", "-o", "c.json")

    assert result.returncode == 0, result.stderr or result.stdout
    assert (tmp_path / "c.json").read_text(encoding="utf-8").splitlines()[0] == "account,sum(position)"
