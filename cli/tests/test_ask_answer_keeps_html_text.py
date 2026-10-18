"""An `ask` answer shows angle-bracket text and HTML blocks literally (w5/548).

Rich's Markdown drops inline and block HTML, so a model's suggested
`--account <ACCOUNT>` printed as `--account ` and a `<div>` holding an amount
vanished: text the model sent disappeared without a trace.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from rich.console import Console

from tests.conftest import StubModel, model_answer
from tests.test_into_glob_create import _env

REPLY = """To open it run: bea add open --account <ACCOUNT> --date <DATE>

The payee was <Amazon Marketplace> and the memo <b>bold</b> x.

<div>
hidden block 99.00 USD
</div>

Still **bold**, `code <kept>`, and [a link](https://example.com).
"""


def _shown(text: str) -> str:
    from cli.ask.render import answer_markdown

    console = Console(width=200, record=True, force_terminal=False, color_system=None)
    console.print(answer_markdown(text))
    return " ".join(console.export_text().split())


def test_every_word_of_the_reply_is_shown() -> None:
    shown = _shown(REPLY)

    for words in (
        "--account <ACCOUNT> --date <DATE>",
        "The payee was <Amazon Marketplace> and the memo <b>bold</b> x.",
        "<div> hidden block 99.00 USD </div>",
    ):
        assert words in shown, shown


def test_markdown_still_renders_and_links_show_their_target() -> None:
    shown = _shown(REPLY)

    assert "Still bold, code <kept>, and a link (https://example.com)." in shown, shown
    assert "**" not in shown


def test_print_mode_prints_the_placeholders(tmp_path: Path, stub_model: StubModel) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text('option "operating_currency" "USD"\n', encoding="utf-8")
    stub_model.reply = lambda n: model_answer(REPLY)
    env = _env(tmp_path)
    env.update(BEA_TOKEN="stub-token", BEA_API_URL=stub_model.url, NO_PROXY="127.0.0.1,localhost", COLUMNS="200")

    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--file", str(ledger), "ask", "--print", "how do I open it?"],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    out = " ".join(result.stdout.split())
    assert "--account <ACCOUNT> --date <DATE>" in out and "99.00 USD" in out, result.stdout
