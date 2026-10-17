"""How an `ask` answer reaches the terminal: Markdown that hides none of its text."""

from __future__ import annotations

from typing import Any

from cli.utils import inert_text


def answer_markdown(text: str) -> Any:
    """The model's answer as Rich Markdown, every character of it shown.

    The answer is model-controlled text on its way to a terminal, so it obeys
    the invariant every untrusted string does (w3/392): no control character
    reaches the screen raw, and a link shows its target instead of becoming an
    OSC 8 hyperlink whose visible text the model chose. Nor may text vanish
    (w1/097): Rich drops inline and block HTML, so `--account <ACCOUNT>` read
    `--account ` and a `<div>` with an amount in it was gone (w5/548). The
    parser here reads HTML as the literal text it is.
    """
    from markdown_it import MarkdownIt
    from rich.markdown import Markdown

    rendered = Markdown(inert_text(text), hyperlinks=False)
    parser = MarkdownIt("commonmark", {"html": False}).enable("strikethrough").enable("table")
    rendered.parsed = parser.parse(rendered.markup)
    return rendered
