"""The `bea ask` write panel never approves on a key meant as "no" (w5/453).

The panel listed "2. No" but bound only arrows, `j`/`k` and Enter, and
started on "Yes": typing `n` or `2` and Enter approved an AI-proposed write.
"""

from __future__ import annotations

import pytest
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from cli.ask.repl import _ask_write_permission


def _press(keys: str) -> str:
    with create_pipe_input() as pipe, create_app_session(input=pipe, output=DummyOutput()):
        pipe.send_text(keys)
        return _ask_write_permission()


@pytest.mark.parametrize(
    ("keys", "answer"),
    [
        ("\r", "n"),  # Enter alone takes the default, which is No.
        ("n\r", "n"),
        ("2\r", "n"),
        ("y\r", "y"),
        ("1\r", "y"),
        ("a\r", "a"),
        ("3\r", "a"),
        ("d\r", "d"),
        ("4\r", "d"),
        ("y2\r", "n"),  # The last choice before Enter wins.
        ("\x1b[A\r", "y"),  # Up from No is Yes, as before.
    ],
)
def test_each_key_selects_its_option(keys: str, answer: str) -> None:
    assert _press(keys) == answer
