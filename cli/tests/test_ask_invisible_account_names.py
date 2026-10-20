"""An AI write cannot hide a format character in a new account name (w5/847).

`2024-01-01 open Assets:Ca\u200bsh USD` showed on the approval panel as
`Assets:Cash`, and approving it wrote a lookalike account that split the
balance into two identical-looking rows. A new name carrying a format
character is now refused before any panel, and the panel shows the ones it
still carries — in a payee, or an account the ledger already opens — as
visible escapes.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from bea_engine import protocol
from bea_engine.ledger import appending
from cli.ask.agent import BqlDeps, WritePermission, make_agent

LEDGER = (
    "2024-01-01 open Assets:Cash USD\n2024-01-01 open Expenses:Food USD\n2024-01-01 open Equity:Opening USD\n"
    '2024-01-02 * "Opening"\n  Assets:Cash  100.00 USD\n  Equity:Opening\n'
)


@pytest.mark.parametrize("mark", ["\u200b", "\u200f", "\u2060", "\u00ad", "\ufeff"])
def test_a_new_account_with_a_format_character_is_refused(tmp_path: Path, mark: str) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    name = f"Assets:Ca{mark}sh"
    text = f'2024-01-01 open {name} USD\n2024-01-20 * "Cafe" "Latte"\n  Expenses:Food  5.00 USD\n  {name}\n'

    with pytest.raises(protocol.UsageError) as refused:
        appending.answer(ledger, text, dry_run=True)

    assert str(refused.value).startswith(f"Write rejected: Invalid account {name!r}. The character U+{ord(mark):04X}")
    assert ledger.read_text() == LEDGER


def test_the_tool_refuses_before_any_panel(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    asked: list[str] = []
    deps = BqlDeps(
        file=ledger, write_permission=WritePermission(confirm_fn=lambda d, t, w, p: (asked.append(d), "y")[1])
    )
    write = make_agent("gpt-4o", "http://unused", "tok")._function_toolset.tools["write_directive"].function

    text = (
        '2024-01-01 open Assets:Ca\u200bsh USD\n2024-01-20 * "Cafe"\n  Expenses:Food  5.00 USD\n  Assets:Ca\u200bsh\n'
    )
    answer = write(SimpleNamespace(deps=deps), text)

    assert answer.startswith("Write rejected")
    assert "U+200B (ZERO WIDTH SPACE)" in answer
    assert asked == []
    assert ledger.read_text() == LEDGER


def test_an_account_the_ledger_already_opens_is_still_written_to(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER + "2024-01-01 open Expenses:Me\u200cal USD\n")

    preview = appending.answer(
        ledger, '2024-01-20 * "Lunch"\n  Expenses:Me\u200cal  5.00 USD\n  Assets:Cash\n', dry_run=True
    )

    assert preview["count"] == 1


def test_the_panel_shows_a_format_character_as_an_escape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from cli.ask import repl

    monkeypatch.setattr(repl, "_ask_write_permission", lambda count=1: "n")
    monkeypatch.setattr(repl, "console", repl.Console(width=100, force_terminal=False, record=True))

    repl.make_confirm_fn([None])(
        '2024-01-20 * "Ca\u200bfe"\n  Expenses:Food  5.00 USD\n  Assets:Cash\n', "main.bean", []
    )

    shown = repl.console.export_text()
    assert '"Ca\\u200bfe"' in shown
    assert "\u200b" not in shown
