"""`bea example` checks its date range whatever the spelling (w5/275).

The range guard compared ISO dates only and let any other spelling through.
`bean-example` reads those too (`2026/03/01`, `March 1 2026`), so an inverted
or too-short range written that way reached the generator and died there with
`IndexError` or `StopIteration` instead of exiting 2.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.mark.parametrize(
    ("args", "named"),
    [
        (["--date-begin", "2026/03/01", "--date-end", "2026/01/01"], "--date-begin '2026/03/01'"),
        (["--date-begin=2024/01/01", "--date-end=2024/01/10"], "--date-begin '2024/01/01'"),
        (["--date-begin", "March 1 2026", "--date-end", "2026-03-10"], "--date-begin 'March 1 2026'"),
        (["--date-begin", "2026-03-01", "--date-end", "2026/01/01"], "--date-end '2026/01/01'"),
        (["--date-end", "20010601"], "--date-end '20010601'"),
    ],
    ids=["slash-inverted", "slash-short", "worded-short", "slash-end-only", "compact-end"],
)
def test_non_iso_date_exits_2_before_generating(tmp_path: Path, args: list[str], named: str) -> None:
    result = _bea(tmp_path, "example", "--seed", "1", *args, "-o", "ex.bean")

    assert result.returncode == 2, result.stderr
    assert f"{named} is not a calendar date in ISO form; write it as YYYY-MM-DD." in result.stderr
    assert "bean-example failed" not in result.stderr
    assert "Traceback" not in result.stderr
    assert result.stdout == ""
    assert not (tmp_path / "ex.bean").exists()


def test_iso_inverted_range_keeps_its_begin_end_message(tmp_path: Path) -> None:
    result = _bea(tmp_path, "example", "--seed", "1", "--date-begin", "2026-03-01", "--date-end", "2026-01-01")

    assert result.returncode == 2, result.stderr
    assert "--date-begin 2026-03-01 is after --date-end 2026-01-01; begin must be on or before end." in result.stderr
    assert "ISO form" not in result.stderr


def test_iso_range_still_generates(tmp_path: Path) -> None:
    result = _bea(tmp_path, "example", "--seed", "1", "--date-begin", "2024-01-01", "--date-end", "2025-01-01")

    assert result.returncode == 0, result.stderr
    assert "Assets:US:BofA:Checking" in result.stdout
