"""How an `ask` answer reaches the terminal: Markdown that hides none of its text."""

from __future__ import annotations

import re
from typing import Any

from cli.utils import inert_text


def _neutralize(tokens: list[Any]) -> None:
    """Escape what the parser decoded, so no control reaches the screen raw.

    `inert_text` runs on the Markdown source, but markdown-it then decodes
    character references back into the characters just escaped: `&#x202E;`
    arrived on the terminal as a raw bidi override (w5/739). Every decoded
    text field and link attribute is neutralized instead; benign entities
    such as `&amp;` still render as the character they name.
    """
    for token in tokens:
        if token.content:
            token.content = inert_text(token.content)
        attrs = token.attrs or {}
        for key, value in attrs.items():
            if isinstance(value, str) and value:
                attrs[key] = inert_text(value)
        if token.children:
            _neutralize(token.children)


def _link_targets(tokens: list[Any]) -> set[tuple[str, str]]:
    """The (href, title) of every link, to tell used reference definitions apart."""
    targets = set()
    for token in tokens:
        if token.type == "link_open":
            attrs = token.attrs or {}
            targets.add((attrs.get("href", ""), attrs.get("title", "")))
        if token.children:
            targets.update(_link_targets(token.children))
    return targets


def _splice_titles(tokens: list[Any]) -> None:
    """Show each link's title at the link, where Rich would otherwise drop it."""
    from markdown_it.token import Token

    for token in tokens:
        children = token.children
        if not children:
            continue
        spliced: list[Any] = []
        index = 0
        while index < len(children):
            child = children[index]
            spliced.append(child)
            if child.type == "link_open" and (child.attrs or {}).get("title"):
                title = Token("text", "", 0)
                title.content = f' "{child.attrs["title"]}"'
                title.level = child.level + 1
                depth = index + 1
                while depth < len(children):
                    closer = children[depth]
                    if closer.type == "link_close" and closer.level == child.level:
                        break
                    spliced.append(closer)
                    depth += 1
                spliced.append(title)
                index = depth - 1  # The outer step lands back on the closer.
            index += 1
        token.children = spliced


def _unused_definitions(source: str, env: dict[str, Any], used: set[tuple[str, str]]) -> list[str]:
    """The source lines of reference definitions no link points at.

    markdown-it emits no tokens for `[label]: url "title"` lines, so an
    answer that only defines references printed nothing of them (w5/739).
    The definer's own lines are sliced back out by the stored line map.
    """
    lines = source.split("\n")
    unused = []
    for _label, reference in (env.get("references") or {}).items():
        if (reference.get("href", ""), reference.get("title", "")) in used:
            continue
        start, end = reference["map"]
        unused.extend(lines[start:end])
    return unused


def _fenced(lines: list[str]) -> str:
    """The lines as a literal block no Markdown construct inside can reopen."""
    longest = max((len(match.group(0)) for line in lines for match in re.finditer(r"`+", line)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"\n{fence}text\n" + "\n".join(lines) + f"\n{fence}\n"


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

    def parse(source: str) -> tuple[Any, dict[str, Any]]:
        parser = MarkdownIt("commonmark", {"html": False}).enable("strikethrough").enable("table")
        env: dict[str, Any] = {}
        return parser.parse(source, env), env

    safe = inert_text(text)
    tokens, env = parse(safe)
    unused = _unused_definitions(safe, env, _link_targets(tokens))
    if unused:
        tokens, _ = parse(safe + _fenced(unused))
    _neutralize(tokens)
    _splice_titles(tokens)
    rendered = Markdown(safe, hyperlinks=False)
    rendered.parsed = tokens
    return rendered
