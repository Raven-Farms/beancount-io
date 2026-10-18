"""A load-cache path an include glob would claim is refused (w5/497).

The cache check compared against existing members only, so a cache under
`include "txns/*.bean"` was written, loaded as ledger text by every later
command, and reported as a file to re-save as UTF-8.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _bea(tmp_path: Path, *args: str, cache_env: str | None = None) -> subprocess.CompletedProcess[str]:
    (tmp_path / "txns").mkdir(exist_ok=True)
    (tmp_path / "txns" / "a.bean").write_text("2024-01-01 open Assets:Cash USD\n")
    (tmp_path / "main.bean").write_text('include "txns/*.bean"\n')
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("BEA_") and k not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    if cache_env is not None:
        env["BEANCOUNT_LOAD_CACHE_FILENAME"] = cache_env
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_the_option_is_refused(tmp_path: Path) -> None:
    result = _bea(tmp_path, "check", "--cache-filename", "txns/zcache.bean")

    assert result.returncode == 2, result.stdout + result.stderr
    assert 'include "txns/*.bean"' in result.stderr and "once the cache is written" in result.stderr
    assert not (tmp_path / "txns" / "zcache.bean").exists()


@pytest.mark.parametrize("command", [("check",), ("balance",), ("list", "open")])
def test_the_environment_variable_is_refused(tmp_path: Path, command: tuple[str, ...]) -> None:
    result = _bea(tmp_path, *command, cache_env="txns/envcache.bean")

    assert result.returncode == 2, result.stdout + result.stderr
    assert "BEANCOUNT_LOAD_CACHE_FILENAME txns/envcache.bean" in result.stderr
    assert "once the cache is written" in result.stderr
    assert not (tmp_path / "txns" / "envcache.bean").exists()


def test_a_cache_outside_the_includes_still_works(tmp_path: Path) -> None:
    result = _bea(tmp_path, "balance", cache_env="elsewhere.pickle")

    assert result.returncode == 0, result.stdout + result.stderr
