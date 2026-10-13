"""`bea example` never calls a ledger its own validation rejects a success (w5/136).

`bean-example` writes `-o`, then validates what it wrote, logs the loader's
errors and exits 0. A range that starts mid-year and crosses January 1 trips a
yearly `balance ... 0 IRAUSD` assertion, so the run exited 0 beside a file
`bea check` refused.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from cli.commands import example

ROOT = Path(__file__).resolve().parents[1]

MID_YEAR = ["--seed", "1", "--date-begin", "2024-06-01", "--date-end", "2025-06-01"]
JANUARY = ["--seed", "1", "--date-begin", "2024-01-01", "--date-end", "2025-06-01"]


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


def test_mid_year_range_exits_1_and_leaves_no_file(tmp_path: Path) -> None:
    result = _bea(tmp_path, "example", *MID_YEAR, "-o", "mid.bean")

    assert result.returncode == 1, result.stderr
    assert not (tmp_path / "mid.bean").exists()
    assert "fails validation" in result.stderr
    assert "Balance failed for 'Assets:US:Federal:PreTax401k'" in result.stderr
    assert "mid.bean was not written" in result.stderr
    assert "Traceback" not in result.stderr
    assert sorted(path.name for path in tmp_path.iterdir() if path.suffix in (".bean", ".tmp")) == []


def test_mid_year_range_prints_no_ledger_on_stdout(tmp_path: Path) -> None:
    result = _bea(tmp_path, "example", *MID_YEAR)

    assert result.returncode == 1, result.stderr
    assert result.stdout == ""
    assert "nothing was printed" in result.stderr


def test_forced_destination_survives_a_rejected_history(tmp_path: Path) -> None:
    victim = tmp_path / "kept.bean"
    victim.write_text("; mine\n")

    result = _bea(tmp_path, "example", *MID_YEAR, "--force", "--output=kept.bean")

    assert result.returncode == 1, result.stderr
    assert victim.read_text() == "; mine\n"


def test_january_range_still_writes_a_ledger_check_accepts(tmp_path: Path) -> None:
    result = _bea(tmp_path, "example", *JANUARY, "-o", "jan.bean")

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert result.stdout == ""
    written = (tmp_path / "jan.bean").read_text()
    assert "Assets:US:Federal:PreTax401k" in written
    # The file is what upstream prints: the same run to stdout is byte-identical.
    assert _bea(tmp_path, "example", *JANUARY).stdout == written
    checked = _bea(tmp_path, "--file", "jan.bean", "check")
    assert checked.returncode == 0, checked.stderr


@pytest.mark.parametrize(
    ("args", "kept"),
    [
        (["-o", "x.bean", "-s", "1"], ["-s", "1"]),
        (["-ox.bean", "-s1"], ["-s1"]),
        (["--output", "x.bean", "--seed=1"], ["--seed=1"]),
        (["--output=x.bean"], []),
        (["-s", "1", "-o"], ["-s", "1", "-o"]),
        (["-o", "x.bean", "--", "-o", "y.bean"], ["--", "-o", "y.bean"]),
    ],
)
def test_output_is_dropped_in_every_spelling(args: list[str], kept: list[str]) -> None:
    assert example._without_output(args) == kept
