"""`bea example` refuses a date span bean-example cannot generate in reasonable time (w5/390).

`--date-begin 0001-01-01` ran a minute and `--date-end 9999-12-31` about
three, then each failed with an upstream class name. The range check now
names the earliest begin (1970-01-01) and the longest span (100 years).
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

import pytest

from cli.commands.example import _check_date_order
from cli.errors import UsageError

ROOT = Path(__file__).resolve().parents[1]


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


@pytest.mark.parametrize(
    ("args", "named"),
    [
        (("--date-begin", "0001-01-01"), "--date-begin 0001-01-01 is before 1970-01-01"),
        (("--date-end", "9999-12-31"), "spans more than 100 years"),
    ],
    ids=["ancient-begin", "far-end"],
)
def test_an_unreasonable_span_is_refused_at_once(tmp_path: Path, args: tuple[str, ...], named: str) -> None:
    started = time.monotonic()
    result = _bea(tmp_path, "example", "--seed", "1", *args)

    assert result.returncode == 2, result.stdout + result.stderr
    assert named in result.stderr
    assert "InvalidOperation" not in result.stderr and "OverflowError" not in result.stderr
    assert time.monotonic() - started < 30


@pytest.mark.parametrize(
    ("begin", "end", "refused"),
    [
        ("1970-01-01", "2026-01-01", None),
        ("1969-12-31", "2026-01-01", "before 1970-01-01"),
        ("1970-01-01", "2070-01-01", None),
        ("1970-01-01", "2070-01-02", "more than 100 years"),
    ],
)
def test_the_bounds_are_exact(begin: str, end: str, refused: str | None) -> None:
    args = ["--date-begin", begin, "--date-end", end]
    if refused is None:
        _check_date_order(args, today=date(2026, 10, 15))
        return
    with pytest.raises(UsageError, match=refused):
        _check_date_order(args, today=date(2026, 10, 15))


def test_a_26_year_history_still_generates(tmp_path: Path) -> None:
    result = _bea(tmp_path, "example", "--seed", "1", "--date-begin", "2000-01-01", "--date-end", "2026-01-01")

    assert result.returncode == 0, result.stderr
    assert "open Assets:" in result.stdout
