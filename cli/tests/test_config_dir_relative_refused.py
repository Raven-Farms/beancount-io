"""A relative `BEA_CONFIG_DIR` is a usage error, not a per-directory state tree (w5/176).

`BEA_CONFIG_DIR=relstate` resolved against the working directory, so every
directory `bea` ran from grew its own `relstate/` and importer settings were
remembered only where they had been written.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from cli import config, update
from cli.errors import UsageError

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """\
option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Equity:Open USD
"""
STATEMENT = "Date,Description,Amount\n2026-02-02,Grocer,-2.00\n"


def _bea(tmp_path: Path, cwd: str, config_dir: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=config_dir,
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    (tmp_path / cwd).mkdir(exist_ok=True)
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        cwd=tmp_path / cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _import_args(tmp_path: Path) -> tuple[str, ...]:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "bank.csv").write_text(STATEMENT)
    return ("-f", str(tmp_path / "main.bean"), "import", str(tmp_path / "bank.csv"), "--account", "Assets:Checking")


def test_relative_config_dir_is_refused_and_creates_nothing(tmp_path: Path) -> None:
    args = _import_args(tmp_path)
    for cwd in ("cwdA", "cwdB"):
        result = _bea(tmp_path, cwd, "relstate", *args)
        assert result.returncode == 2, result.stderr
        assert "BEA_CONFIG_DIR must be an absolute path, got 'relstate'" in result.stderr
        assert result.stdout == ""
        assert not (tmp_path / cwd / "relstate").exists()


def test_relative_config_dir_is_a_json_usage_error(tmp_path: Path) -> None:
    result = _bea(tmp_path, "cwdA", "relstate", "--json", *_import_args(tmp_path))
    assert result.returncode == 2
    error = json.loads(result.stderr)["error"]
    assert error["category"] == "usage"
    assert "BEA_CONFIG_DIR" in error["message"]
    assert not (tmp_path / "cwdA" / "relstate").exists()


def test_relative_config_dir_fails_a_command_that_keeps_no_state(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    result = _bea(tmp_path, "cwdA", "relstate", "-f", str(tmp_path / "main.bean"), "list", "accounts")
    assert result.returncode == 2
    assert "BEA_CONFIG_DIR" in result.stderr


def test_absolute_config_dir_shares_importer_memory_across_directories(tmp_path: Path) -> None:
    args = _import_args(tmp_path)
    state = str(tmp_path / "state")
    first = _bea(tmp_path, "cwdA", state, *args)
    second = _bea(tmp_path, "cwdB", state, *args)
    assert (first.returncode, second.returncode) == (0, 0), first.stderr + second.stderr
    assert "Read the column mapping from the header row" in first.stderr
    assert "Using remembered settings for bank.csv" in second.stderr


def test_version_still_answers_under_a_relative_config_dir(tmp_path: Path) -> None:
    result = _bea(tmp_path, "cwdA", "relstate", "--version")
    assert result.returncode == 0
    assert result.stdout.startswith("bea ")
    assert not (tmp_path / "cwdA" / "relstate").exists()


def test_config_dir_accepts_absolute_home_and_empty_values(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("BEA_CONFIG_DIR", "relstate")
    with pytest.raises(UsageError, match="BEA_CONFIG_DIR"):
        config.config_dir()
    # The version hint reads the update cache from this directory and stays silent.
    assert update.read_cache() is None
    monkeypatch.setenv("BEA_CONFIG_DIR", "~/state")
    assert config.config_dir() == tmp_path / "state"
    monkeypatch.setenv("BEA_CONFIG_DIR", "")
    assert config.config_dir() == tmp_path / ".config" / "bea"
