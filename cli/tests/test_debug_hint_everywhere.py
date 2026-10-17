"""Every error with a hidden traceback says how to see it (w5/424).

Only engine failures added "Pass --debug before the command for a
traceback". An unexpected frontend exception and a crashed upstream program
printed a bare class name, though `--debug` shows a traceback for both.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.commands import treeify as treeify_command
from cli.main import app

ROOT = Path(__file__).resolve().parents[1]
HINT = "Pass --debug before the command for a traceback."


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "bal.txt").write_text("Assets:Cash  5\nAssets:Bank  7\n")
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
        timeout=60,
        stdin=subprocess.DEVNULL,
    )


def test_a_crashed_upstream_program_carries_the_hint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A native child that died with a traceback. bea now refuses non-UTF-8
    # treeify input itself (w5/535), so the crash is simulated at the boundary.
    (tmp_path / "bal.txt").write_text("Assets:Cash  5\n")
    crash = (
        "Traceback (most recent call last):\n"
        '  File "treeify", line 1, in <module>\n'
        "UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9 in position 10: invalid continuation byte\n"
    )

    def crashed(*args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["treeify"], 1, "", crash)

    monkeypatch.setattr(treeify_command.launch, "capture_native", crashed)
    runner = CliRunner()

    plain = runner.invoke(app, ["treeify", str(tmp_path / "bal.txt")])
    assert plain.exit_code == 1, plain.output
    assert "UnicodeDecodeError" in plain.stderr
    assert plain.stderr.rstrip().endswith(f". {HINT}")
    assert "Traceback" not in plain.stderr

    debug = runner.invoke(app, ["--debug", "treeify", str(tmp_path / "bal.txt")])
    assert "Traceback (most recent call last)" in debug.stderr
    assert HINT not in debug.stderr


def test_an_unexpected_frontend_exception_carries_the_hint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "bal.txt").write_text("Assets:Cash  5\n")

    def explode(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("frontend went wrong")

    monkeypatch.setattr(treeify_command.launch, "capture_native", explode)
    runner = CliRunner()

    plain = runner.invoke(app, ["treeify", str(tmp_path / "bal.txt")])
    assert plain.exit_code == 1
    assert f"Error: frontend went wrong. {HINT}" in plain.stderr

    debug = runner.invoke(app, ["--debug", "treeify", str(tmp_path / "bal.txt")])
    assert "Traceback (most recent call last)" in debug.stderr
    assert HINT not in debug.stderr


def test_a_refusal_has_no_hint(tmp_path: Path) -> None:
    refused = _bea(tmp_path, "treeify", "missing.txt")
    assert refused.returncode != 0
    assert HINT not in refused.stderr
