"""Upstream usage errors name the `bea` command the user ran (w5/624).

`bea check --nosuch`, `bea doctor lex` and `bea example --nosuch` passed
upstream's `Usage: bean-check …` and `Try 'bean-check --help' for help.`
through, naming programs bea users never install.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

ROOT = Path(__file__).resolve().parents[1]


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text("2026-01-01 open Assets:Cash USD\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
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
        check=False,
    )


@pytest.mark.parametrize(
    ("args", "command"),
    [
        (["-f", "main.bean", "check", "--nosuch"], "bea check"),
        (["doctor", "lex"], "bea doctor lex"),
        (["doctor", "context", "main.bean"], "bea doctor context"),
        (["example", "--nosuch"], "bea example"),
    ],
    ids=["check", "doctor-lex", "doctor-context", "example"],
)
def test_a_usage_error_names_the_bea_command(tmp_path: Path, args: list[str], command: str) -> None:
    result = _bea(tmp_path, *args)

    assert result.returncode == 2, result.stderr
    assert f"Try '{command} --help' for help." in result.stderr
    assert f"Usage: {command} " in result.stderr
    assert "bean-" not in "".join(line for line in result.stderr.splitlines() if "Try '" in line or "Usage:" in line)


def test_a_captured_run_is_renamed_too(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text("2026-01-01 open Assets:Cash USD\n")

    result = CliRunner().invoke(app, ["-f", str(tmp_path / "main.bean"), "check", "--nosuch"])

    assert result.exit_code == 2, result.output
    assert "Try 'bea check --help' for help." in result.stderr
