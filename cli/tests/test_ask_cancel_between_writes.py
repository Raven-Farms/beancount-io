"""Ctrl-C between a reply's writes stops the queued ones (w5/731).

w5/544 serialized a reply's `write_directive` calls behind a lock, but the
workers outlived an interrupted turn: each later ran its dry run, its own
confirm panel and its write. The next panel drew over the returned prompt,
an approved write landed after the turn was cancelled, the report never
named the write that already landed, and a panel left showing held the
process open past Ctrl-D. A per-turn flag now cancels every write that has
not shown its panel, and the REPL joins the in-flight write before
reporting it.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from cli.ask.agent import BqlDeps, WritePermission, make_agent, translated_failures
from cli.engine import launch
from tests.conftest import StubModel, model_answer

LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD
"""
LATTE = '2026-02-01 * "Cafe" "latte"\n  Expenses:Food  5.25 USD\n  Assets:Cash\n'
BREAD = '2026-02-02 * "Bakery" "bread"\n  Expenses:Food  3.00 USD\n  Assets:Cash\n'


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(LEDGER, encoding="utf-8")
    return path


def _reply(results: list[str], *directives: str) -> Callable[[list[ModelMessage], AgentInfo], ModelResponse]:
    """One reply holding every directive, then a text answer collecting the tool results."""

    def reply(messages: list[ModelMessage], _info: AgentInfo) -> ModelResponse:
        returned = [part for message in messages for part in message.parts if isinstance(part, ToolReturnPart)]
        if returned:
            results.extend(str(part.content) for part in returned)
            return ModelResponse(parts=[TextPart("done")])
        return ModelResponse(
            parts=[
                ToolCallPart("write_directive", {"directive": text}, tool_call_id=f"call-{n}")
                for n, text in enumerate(directives)
            ]
        )

    return reply


def test_a_cancelled_turn_shows_no_panel_and_writes_nothing(ledger: Path) -> None:
    shown: list[str] = []
    results: list[str] = []
    agent = make_agent("model", base_url="http://127.0.0.1:9", api_key="test")
    deps = BqlDeps(
        file=ledger,
        write_permission=WritePermission(confirm_fn=lambda d, t, w: (shown.append(d), "y")[1]),
    )
    deps.cancel_event.set()

    with agent.override(model=FunctionModel(_reply(results, LATTE, BREAD))):
        agent.run_sync("add both", deps=deps)

    assert shown == []
    assert results == ["Write cancelled", "Write cancelled"], results
    assert ledger.read_text(encoding="utf-8") == LEDGER


def test_a_cancel_during_the_first_panel_cancels_that_write_too(ledger: Path) -> None:
    shown: list[str] = []
    results: list[str] = []
    agent = make_agent("model", base_url="http://127.0.0.1:9", api_key="test")
    deps = BqlDeps(file=ledger, write_permission=WritePermission())

    def confirm(directive: str, _target: str, _warnings: list[str]) -> str:
        shown.append(directive)
        deps.cancel_event.set()
        return "y"

    deps.write_permission.confirm_fn = confirm
    with agent.override(model=FunctionModel(_reply(results, LATTE, BREAD))):
        agent.run_sync("add both", deps=deps)

    assert len(shown) == 1
    assert sorted(results) == ["Write cancelled", "Write cancelled"], results
    assert ledger.read_text(encoding="utf-8") == LEDGER


def test_a_cancel_during_a_later_dry_run_keeps_the_landed_write(ledger: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    shown: list[str] = []
    results: list[str] = []
    agent = make_agent("model", base_url="http://127.0.0.1:9", api_key="test")
    deps = BqlDeps(
        file=ledger,
        write_permission=WritePermission(confirm_fn=lambda d, t, w: (shown.append(d), "y")[1]),
    )
    real = launch.helper_json
    calls = 0

    def hooked(argv: list[str], **kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        if calls == 3:
            # The second worker's dry run starts only after the first write
            # landed: the lock serializes the two (w5/544).
            deps.cancel_event.set()
        return real(argv, **kwargs)

    monkeypatch.setattr(launch, "helper_json", hooked)
    with agent.override(model=FunctionModel(_reply(results, LATTE, BREAD))):
        agent.run_sync("add both", deps=deps)

    assert len(shown) == 1
    assert sorted(results) == [f"Added 1 directive(s) to {ledger}.", "Write cancelled"], results
    written = ledger.read_text(encoding="utf-8")
    assert ("latte" in written) != ("bread" in written), written
    assert deps.writes == [(1, str(ledger))]


def test_the_next_turn_starts_uncancelled(ledger: Path) -> None:
    deps = BqlDeps(file=ledger)
    deps.cancel_event.set()

    with translated_failures(deps):
        pass

    assert not deps.cancel_event.is_set()


# ── end to end on a real terminal ──────────────────────────────────────────


def _three_calls(*directives: str) -> dict[str, object]:
    """One reply holding three `write_directive` calls, OpenAI protocol shape."""
    return {
        "index": 0,
        "finish_reason": "tool_calls",
        "message": {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": f"call-{n}",
                    "type": "function",
                    "function": {"name": "write_directive", "arguments": json.dumps({"directive": text})},
                }
                for n, text in enumerate(directives)
            ],
        },
    }


def _big_ledger(path: Path, transactions: int = 30000) -> None:
    """A ledger slow enough that Ctrl-C lands mid-write, not on a later panel.

    Each dry run and each write loads the whole file (~3 s at 30,000 small
    transactions), so the 1.5 s of terminal quiet before the harness sends
    Ctrl-C always falls inside the approved write or the next dry run.
    """
    lines = [
        'option "operating_currency" "USD"',
        "2026-01-01 open Assets:Cash USD",
        "2026-01-01 open Expenses:Food USD",
    ]
    for n in range(transactions):
        lines.append(f'2026-01-{(n % 27) + 1:02d} * "Shop" "item{n}"\n  Expenses:Food  1.00 USD\n  Assets:Cash')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_ctrl_c_between_writes_names_the_landed_one_and_exits(
    tmp_path: Path, stub_model: StubModel, ask_on_a_terminal: Any
) -> None:
    ledger = tmp_path / "main.bean"
    _big_ledger(ledger)
    names = ("Alpha", "Bravo", "Charlie")
    writes = [
        f'2026-02-0{n + 1} * "Cafe" "{name}"\n  Expenses:Food  5.25 USD\n  Assets:Cash' for n, name in enumerate(names)
    ]
    stub_model.reply = lambda n: _three_calls(*writes) if n == 1 else model_answer("Done.")

    run = ask_on_a_terminal(
        ["--file", str(ledger), "ask"],
        [
            "add three",
            "@ENTER",
            "@WAIT:Append this directive to the ledger",
            "y",  # The panel starts on No (w5/453).
            "@ENTER",
            "@CTRL_C",
            "@WAIT:(cancelled",
            "@WAIT:❯",
            "@CTRL_D",
        ],
    )

    Path("/tmp/731screen.txt").write_bytes(run.emitted)
    assert run.status == 0, run.screen
    assert stub_model.count == 1, "the cancelled turn sent a follow-up request"
    assert "(cancelled" in run.screen
    assert "already written 1 directive(s)" in run.screen, "the landed write was not named"
    after = run.emitted.split(b"(cancelled", 1)[1]
    assert b"Append this directive to the ledger" not in after, "a panel drew after the cancel"
    assert b"Goodbye." in after
    written = ledger.read_text(encoding="utf-8")
    assert sum(name in written for name in names) == 1, "zero or several writes landed"
