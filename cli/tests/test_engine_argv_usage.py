"""Parser refusals have an envelope; arbitrary exit 2 has no known outcome (w5/673)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from cli.engine import launch
from cli.errors import BeaError, ConflictError, UsageError

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("writes", [False, True], ids=["reader", "writer"])
def test_real_engine_argument_refusal_is_a_usage_error(writes: bool) -> None:
    with pytest.raises(UsageError, match="No such option: --not-an-engine-option") as raised:
        launch.helper_json(["add", "--not-an-engine-option"], writes=writes)
    assert raised.value.exit_code == 2
    assert "did not answer" not in str(raised.value)
    assert "outcome is unknown" not in str(raised.value)


@pytest.mark.parametrize(
    ("args", "reason"),
    [
        (["add", "--bad-option"], "No such option: --bad-option"),
        (["add", "--file", "main.bean", "--type", "open"], "Missing option '--request'"),
        (["not-a-command"], "No such command 'not-a-command'"),
    ],
    ids=["unknown-option", "missing-option", "unknown-command"],
)
def test_engine_parser_errors_answer_one_usage_envelope(args: list[str], reason: str) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "bea_engine", *args],
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    answer = json.loads(result.stdout)
    assert answer["ok"] is False
    assert answer["error"]["category"] == "usage"
    assert reason in answer["error"]["message"]
    assert result.stderr == ""


@pytest.mark.parametrize(
    ("stdout", "stderr"),
    [
        ("", ""),
        ("", "plugin stopped after writing"),
        ("", "Usage: another-program [OPTIONS]\nError: bad argument\n"),
        ("", "Usage: bea-engine add [OPTIONS]\nError: bad argument\n"),
        ("", "Usage: bea-engine add [OPTIONS]\nError: bad argument\nTraceback (most recent call last):\n"),
        ("wrote one entry\n", "Usage: bea-engine add [OPTIONS]\nError: bad argument\n"),
    ],
    ids=["silent", "plugin", "other-program", "nested-click", "traceback", "partial-stdout"],
)
def test_exit_two_without_an_envelope_keeps_unknown_write_outcome(stdout: str, stderr: str) -> None:
    completed = subprocess.CompletedProcess(["bea-engine"], 2, stdout, stderr)
    with pytest.raises(ConflictError, match="outcome is unknown") as raised:
        launch._parse(completed, ["add"], writes=True)
    assert raised.value.exit_code == 4


def test_a_silent_reader_exit_two_is_still_an_engine_failure() -> None:
    completed = subprocess.CompletedProcess(["bea-engine"], 2, "", "")
    with pytest.raises(BeaError, match="did not answer") as raised:
        launch._parse(completed, ["check"])
    assert raised.value.exit_code == 1


@pytest.mark.parametrize(("exception", "code"), [("EOFError", 1), ("KeyboardInterrupt", 130)])
def test_engine_entry_preserves_parser_abort_and_interrupt_status(exception: str, code: int) -> None:
    script = (
        "import runpy, sys\n"
        "from bea_engine.main import app\n"
        "@app.command()\n"
        "def interrupted():\n"
        f"    raise {exception}()\n"
        "sys.argv = ['bea_engine', 'interrupted']\n"
        "runpy.run_module('bea_engine', run_name='__main__')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == code, result.stdout + result.stderr
    assert "Traceback" not in result.stderr
    assert result.stdout == ""
    if exception == "EOFError":
        assert "Aborted" in result.stderr
