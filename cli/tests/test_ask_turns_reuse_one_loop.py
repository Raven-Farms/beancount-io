"""Each `bea ask` session turn sends its question once, even on a kept-alive connection (w5/545).

Each turn ran on a new event loop, since the prompt between turns runs its
own, while the cached HTTP client kept the last turn's keep-alive
connection, bound to the old loop. Reading the reply failed, the SDK retried
on a new connection, and a question asked within a few seconds of the last
answer reached the proxy twice; the first, billed, answer was discarded.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.conftest import StubModel, model_answer


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text('option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n', encoding="utf-8")
    return path


def test_two_quick_turns_send_two_requests(ledger: Path, stub_model: StubModel, ask_on_a_terminal: Any) -> None:
    stub_model.keep_alive = True
    stub_model.reply = lambda n: model_answer(f"answer {n}")

    run = ask_on_a_terminal(
        ["--file", str(ledger), "ask"],
        ["first", "@ENTER", "@WAIT:answer 1", "@WAIT:❯", "second", "@ENTER", "@WAIT:answer", "@WAIT:❯", "@CTRL_D"],
        timeout=60,
        env_overrides={"BEA_NO_ASK_HISTORY": "1"},
    )

    assert run.status == 0, run.screen
    assert stub_model.count == 2, f"{stub_model.count} requests for two questions"
    assert "answer 2" in run.screen and "answer 3" not in run.screen
