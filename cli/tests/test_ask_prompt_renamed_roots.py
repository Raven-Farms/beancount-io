"""`bea ask` tells the model the ledger's own account roots (w5/403).

The prompt's recipes filter on `^Expenses` and `^(Assets|Liabilities)`, so on
a ledger with `option "name_expenses" "Aufwand"` a model following them
queried roots that hold nothing and read the 0 rows as no data.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_ai.messages import ModelMessage, ModelResponse, SystemPromptPart, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from cli.ask.agent import BqlDeps, make_agent


def _system_prompt(ledger: Path) -> list[str]:
    seen: list[str] = []

    def reply(messages: list[ModelMessage], _info: AgentInfo) -> ModelResponse:
        seen.extend(
            part.content for message in messages for part in message.parts if isinstance(part, SystemPromptPart)
        )
        return ModelResponse(parts=[TextPart("ok")])

    agent = make_agent("model", base_url="http://127.0.0.1:9", api_key="test")
    with agent.override(model=FunctionModel(reply)):
        agent.run_sync("What did I spend?", deps=BqlDeps(file=ledger))
    return seen


def test_renamed_roots_are_named_to_the_model(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text('option "name_assets" "Aktiva"\noption "name_expenses" "Aufwand"\n')

    parts = _system_prompt(ledger)

    assert parts[-1] == (
        "This ledger renames its account roots: Aktiva (for Assets), Aufwand (for Expenses). Use those names "
        "wherever the examples above say Assets, Expenses, as in account ~ '^Aktiva' rather than '^Assets'."
    )


def test_a_default_ledger_gets_the_prompt_unchanged(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text('option "operating_currency" "USD"\noption "name_assets" "Assets"\n')

    parts = _system_prompt(ledger)

    assert len(parts) == 2
    assert not any("renames its account roots" in part for part in parts)
