"""An answer cut off at the CLI's own output cap says so (w5/546).

`bea ask` caps each answer at `MAX_OUTPUT_TOKENS`, and an answer that reached
it (`finish_reason: "length"`) printed as if complete, exit 0 — a figure can
end mid-number. It now carries a notice, and `--print` exits nonzero.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import StubModel, model_answer
from tests.test_into_glob_create import _env

CUT = "Your total spend in January was 1"
CUT_OFF_NOTICE = "The answer reached the per-answer limit and was cut off; ask a narrower question."


def _cut(text: str) -> dict[str, object]:
    return {**model_answer(text), "finish_reason": "length"}


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text('option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n', encoding="utf-8")
    return path


def _print(tmp_path: Path, ledger: Path, stub: StubModel) -> subprocess.CompletedProcess[str]:
    env = _env(tmp_path)
    env.update(BEA_TOKEN="stub-token", BEA_API_URL=stub.url, NO_PROXY="127.0.0.1,localhost")
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--file", str(ledger), "ask", "--print", "How much did I spend?"],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_print_mode_shows_the_part_and_exits_nonzero(tmp_path: Path, ledger: Path, stub_model: StubModel) -> None:
    stub_model.reply = lambda n: _cut(CUT)

    result = _print(tmp_path, ledger, stub_model)

    assert result.returncode == 1, result.stdout + result.stderr
    assert CUT in result.stdout
    assert result.stderr.strip().endswith(f"Error: {CUT_OFF_NOTICE}"), result.stderr
    assert stub_model.count == 1


def test_a_finished_answer_is_the_control(tmp_path: Path, ledger: Path, stub_model: StubModel) -> None:
    stub_model.reply = lambda n: model_answer(CUT)

    result = _print(tmp_path, ledger, stub_model)

    assert result.returncode == 0, result.stderr
    assert CUT in result.stdout and CUT_OFF_NOTICE not in result.stdout + result.stderr


def test_the_session_follows_the_part_with_the_notice(
    ledger: Path, stub_model: StubModel, ask_on_a_terminal: Any
) -> None:
    stub_model.reply = lambda n: _cut(CUT)

    run = ask_on_a_terminal(
        ["--file", str(ledger), "ask"],
        ["how much", "@ENTER", f"@WAIT:{CUT}", "@WAIT:❯", "@CTRL_D"],
        timeout=60,
        env_overrides={"BEA_NO_ASK_HISTORY": "1"},
    )

    assert run.status == 0, run.screen
    screen = " ".join(run.screen.split())
    assert screen.index(CUT) < screen.index(CUT_OFF_NOTICE), run.screen
