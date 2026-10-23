"""An `ask` answer escapes character references and shows references and titles (w5/739).

`inert_text` ran on the Markdown source, but markdown-it then decoded
character references back into the characters just escaped, so `&#x202E;`
reached the terminal as a raw bidi override that could display `00.001` as
`100.00`. Reference definitions emitted no tokens at all, so their URLs and
titles vanished, and inline link titles were dropped too.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from rich.console import Console

from tests.conftest import StubModel, model_answer
from tests.test_into_glob_create import _env

ENTITY_REPLY = "Paid &#x202E;00.001&#x202C; USD to Bob; raw \u202e is escaped"
ISOLATE_REPLY = "x &#8238; y &#x2066;z&#x2069; &#27; e"
REFS_REPLY = 'Sources:\n\n[1]: https://beancount.io/docs/a\n[2]: https://example.com/b "Fee 12.00 USD"\n\nEnd.'
TITLE_REPLY = 'See [docs](https://example.com "The Title") now.'
USED_REPLY = "Use [a][1].\n\n[1]: https://beancount.io/docs/a\n[2]: https://example.com/b\n"


def _shown(text: str) -> str:
    from cli.ask.render import answer_markdown

    console = Console(width=200, record=True, force_terminal=False, color_system=None)
    console.print(answer_markdown(text))
    return " ".join(console.export_text().split())


def test_character_references_are_escaped_not_raw() -> None:
    shown = _shown(ENTITY_REPLY)

    assert "\u202e" not in shown and "\u202c" not in shown, repr(shown)
    assert "Paid \\u202e00.001\\u202c USD to Bob; raw \\u202e is escaped" in shown, shown


def test_isolates_and_decimal_references_are_escaped_not_raw() -> None:
    shown = _shown(ISOLATE_REPLY)

    assert "\u202e" not in shown and "\u2066" not in shown and "\u2069" not in shown, repr(shown)
    assert "\x1b" not in shown, repr(shown)
    assert "x \\u202e y \\u2066z\\u2069" in shown, shown


def test_benign_entities_still_render_as_the_character() -> None:
    assert _shown("Fish &amp; chips &lt;3 &#65;") == "Fish & chips <3 A"


def test_reference_definitions_show_their_urls_and_title() -> None:
    shown = _shown(REFS_REPLY)

    assert "https://beancount.io/docs/a" in shown, shown
    assert 'https://example.com/b "Fee 12.00 USD"' in shown, shown
    assert shown.startswith("Sources:") and "End." in shown


def test_a_link_title_shows_at_its_link() -> None:
    shown = _shown(TITLE_REPLY)

    assert 'docs "The Title" (https://example.com)' in shown, shown


def test_a_used_reference_is_not_repeated() -> None:
    shown = _shown(USED_REPLY)

    assert "Use a (https://beancount.io/docs/a)." in shown, shown
    assert shown.count("https://beancount.io/docs/a") == 1, shown
    assert "[2]: https://example.com/b" in shown, shown


def test_print_mode_escapes_entities_end_to_end(tmp_path: Path, stub_model: StubModel) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text('option "operating_currency" "USD"\n', encoding="utf-8")
    stub_model.reply = lambda n: model_answer(ENTITY_REPLY)
    env = _env(tmp_path)
    env.update(BEA_TOKEN="stub-token", BEA_API_URL=stub_model.url, NO_PROXY="127.0.0.1,localhost", COLUMNS="200")

    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--file", str(ledger), "ask", "--print", "what did I pay?"],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert "\u202e" not in result.stdout and "\u202c" not in result.stdout
    assert "Paid \\u202e00.001\\u202c USD to Bob" in result.stdout, result.stdout
