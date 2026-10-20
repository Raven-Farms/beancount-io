"""Two `write_directive` calls in one model reply are approved one at a time (w5/544).

Models batch independent calls ("add a coffee and a lunch"), and pydantic-ai
ran both writes at once in worker threads: two consent selectors shared one
terminal, an answer reached either panel, both dry runs predated either
write so approving both wrote one, and the session could hang.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from cli.ask.agent import BqlDeps, WritePermission, make_agent

LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD
"""
LATTE = '2026-02-01 * "Cafe" "latte"\n  Expenses:Food  5.25 USD\n  Assets:Cash\n'
BREAD = '2026-02-02 * "Bakery" "bread"\n  Expenses:Food  3.00 USD\n  Assets:Cash\n'


def _run(ledger: Path, answers: dict[str, str]) -> tuple[list[str], list[str], int]:
    """Run one reply holding both writes; returns the panels shown, the tool results and peak overlap."""
    shown: list[str] = []
    results: list[str] = []
    active = 0
    peak = 0
    guard = threading.Lock()

    def confirm(directive: str, _target: str, _warnings: list[str], _proposal: object) -> str:
        nonlocal active, peak
        with guard:
            active += 1
            peak = max(peak, active)
            shown.append(directive)
        time.sleep(0.2)  # long enough for a concurrent call to reach its own panel
        with guard:
            active -= 1
        return next(answer for narration, answer in answers.items() if narration in directive)

    def reply(messages: list[ModelMessage], _info: AgentInfo) -> ModelResponse:
        returned = [part for message in messages for part in message.parts if isinstance(part, ToolReturnPart)]
        if returned:
            results.extend(str(part.content) for part in returned)
            return ModelResponse(parts=[TextPart("done")])
        return ModelResponse(
            parts=[
                ToolCallPart("write_directive", {"directive": LATTE}, tool_call_id="latte"),
                ToolCallPart("write_directive", {"directive": BREAD}, tool_call_id="bread"),
            ]
        )

    agent = make_agent("model", base_url="http://127.0.0.1:9", api_key="test")
    deps = BqlDeps(file=ledger, write_permission=WritePermission(confirm_fn=confirm))
    with agent.override(model=FunctionModel(reply)):
        agent.run_sync("add both", deps=deps)
    return shown, results, peak


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(LEDGER, encoding="utf-8")
    return path


def test_approving_both_writes_both(ledger: Path) -> None:
    shown, results, peak = _run(ledger, {"latte": "y", "bread": "y"})

    assert peak == 1, "two consent panels were open at once"
    assert len(shown) == 2
    assert sorted(results) == [f"Added 1 directive(s) to {ledger}."] * 2, results
    written = ledger.read_text(encoding="utf-8")
    assert '"latte"' in written and '"bread"' in written


def test_each_answer_applies_to_the_directive_on_its_panel(ledger: Path) -> None:
    shown, results, peak = _run(ledger, {"latte": "y", "bread": "n"})

    assert peak == 1
    assert sorted(results) == sorted([f"Added 1 directive(s) to {ledger}.", "Write cancelled by user."]), results
    written = ledger.read_text(encoding="utf-8")
    assert '"latte"' in written and '"bread"' not in written
