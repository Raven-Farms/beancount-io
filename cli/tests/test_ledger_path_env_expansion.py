"""A `$NAME` in the ledger path is refused when Beancount would expand it (w5/315).

Beancount's loader runs `expandvars` on the root path, so with X set a read
of `$X.bean` loaded `decoy.bean` and reported its balances with exit 0, while
`add` wrote the literal `$X.bean`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REAL = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Equity:Opening
2026-01-02 * "REAL"
  Assets:Checking  100.00 USD
  Equity:Opening
"""
DECOY = REAL.replace("REAL", "DECOY").replace("100.00", "999.00")


def _bea(tmp_path: Path, *args: str, **env_overrides: str | None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    for key, value in env_overrides.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "$X.bean").write_text(REAL)
    (tmp_path / "decoy.bean").write_text(DECOY)
    return tmp_path


@pytest.mark.parametrize(
    "command",
    [
        ["balance"],
        ["list", "transaction"],
        ["check"],
        ["add", "note", "--date", "2026-01-05", "-a", "Assets:Checking", "-m", "hi"],
    ],
)
def test_a_set_variable_is_refused_not_read_from_another_file(books: Path, command: list[str]) -> None:
    before = (books / "$X.bean").read_text()
    result = _bea(books, "-f", str(books / "$X.bean"), *command, X="decoy")
    assert result.returncode == 2, result.stderr
    assert "would expand" in result.stderr
    assert "decoy.bean" in result.stderr  # The file it would have read instead.
    assert "999.00" not in result.stdout and "DECOY" not in result.stdout
    assert (books / "$X.bean").read_text() == before  # Nothing written either.


def test_doctor_refuses_the_same_path(books: Path) -> None:
    result = _bea(books, "doctor", "context", str(books / "$X.bean"), "4", X="decoy")
    assert result.returncode == 2, result.stderr
    assert "would expand" in result.stderr
    assert "DECOY" not in result.stdout


def test_home_in_the_name_is_refused(tmp_path: Path) -> None:
    (tmp_path / "$HOME.bean").write_text(REAL)
    result = _bea(tmp_path, "-f", str(tmp_path / "$HOME.bean"), "balance", HOME=str(tmp_path / "nowhere"))
    assert result.returncode == 2, result.stderr
    assert "would expand" in result.stderr


def test_a_variable_in_a_parent_directory_is_refused(tmp_path: Path) -> None:
    (tmp_path / "sub$X").mkdir()
    (tmp_path / "sub$X" / "main.bean").write_text(REAL)
    (tmp_path / "subdecoy").mkdir()
    (tmp_path / "subdecoy" / "main.bean").write_text(DECOY)
    result = _bea(tmp_path, "-f", str(tmp_path / "sub$X" / "main.bean"), "balance", X="decoy")
    assert result.returncode == 2, result.stderr
    assert "would expand" in result.stderr


def test_an_unset_variable_reads_the_file_as_written(books: Path) -> None:
    result = _bea(books, "-f", str(books / "$X.bean"), "balance", X=None)
    assert result.returncode == 0, result.stderr
    assert "100.00" in result.stdout
    assert "999.00" not in result.stdout
