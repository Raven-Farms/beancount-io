"""The `ask` approval panel shows the aligned text the engine will append (w5/374).

A model that indents with tabs got a panel of `\\x09Expenses:Food\\x094 USD`,
while the engine accepted the tabs and wrote the posting aligned with spaces,
so the panel was neither readable nor what was written. The dry run now returns
the lines the commit appends, and the panel shows those. A real control
character is still refused before any panel.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from bea_engine.ledger import appending
from cli.ask.agent import BqlDeps, WritePermission, make_agent

LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD
"""
TABBED = '2026-02-01 * "Cafe" "coffee"\n\tExpenses:Food\t4 USD\n\tAssets:Cash\t\t-4.000 USD\n'


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    file = tmp_path / "main.bean"
    file.write_text(LEDGER, encoding="utf-8")
    return file


def _write_tool(agent: Any) -> Any:
    return agent._function_toolset.tools["write_directive"].function


def test_the_dry_run_text_is_exactly_what_the_commit_appends(ledger: Path) -> None:
    preview = appending.answer(ledger, TABBED, dry_run=True)
    before = ledger.read_text(encoding="utf-8")

    appending.answer(ledger, TABBED, token=preview["token"])

    appended = ledger.read_text(encoding="utf-8")[len(before) :]
    assert preview["text"] == appended.strip("\n") + "\n"
    assert "\t" not in preview["text"]
    assert "  Expenses:Food" in preview["text"]


def test_the_panel_shows_the_aligned_text_and_it_is_what_lands(ledger: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from cli.ask import repl

    shown: list[str] = []
    agent = make_agent("gpt-4o", "http://unused", "tok")
    deps = BqlDeps(file=ledger, write_permission=WritePermission(confirm_fn=lambda d, t, w: (shown.append(d), "y")[1]))
    before = ledger.read_text(encoding="utf-8")

    answer = _write_tool(agent)(SimpleNamespace(deps=deps), TABBED)

    assert answer.startswith("Added 1 directive(s)"), answer
    assert shown[0] == ledger.read_text(encoding="utf-8")[len(before) :].strip("\n") + "\n"
    monkeypatch.setattr(repl, "_ask_write_permission", lambda: "y")
    monkeypatch.setattr(repl, "console", repl.Console(width=100, force_terminal=False, record=True))
    repl.make_confirm_fn([None])(shown[0], str(ledger), [])
    panel = repl.console.export_text()
    assert "\\x09" not in panel
    assert "Expenses:Food" in panel


def test_a_real_control_character_is_still_refused_before_any_panel(ledger: Path) -> None:
    shown: list[str] = []
    agent = make_agent("gpt-4o", "http://unused", "tok")
    deps = BqlDeps(file=ledger, write_permission=WritePermission(confirm_fn=lambda d, t, w: (shown.append(d), "y")[1]))

    answer = _write_tool(agent)(SimpleNamespace(deps=deps), TABBED.replace('"coffee"', '"coffee\x07"'))

    assert "Write rejected" in answer
    assert shown == []
    assert ledger.read_text(encoding="utf-8") == LEDGER
