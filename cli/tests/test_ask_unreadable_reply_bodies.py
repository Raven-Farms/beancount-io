"""More replies the AI SDK cannot read get the unexpected-response sentence (w5/547).

w5/373 mapped a reply the SDK cannot parse to `Unexpected server response
(HTTP 200)`, but a body cut inside a UTF-8 character or sent in another
charset printed the codec's own message, one nested past the parser's depth
`maximum recursion depth exceeded`, and a `"type": "custom"` tool call
`Custom tool calls are not supported` — and in a session, after an approved
write, none of them said the write had landed.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import StubModel, model_tool_call
from tests.test_into_glob_create import _env


def _completion(message: dict[str, object]) -> dict[str, object]:
    return {
        "id": "chatcmpl-stub",
        "object": "chat.completion",
        "created": 0,
        "model": "gpt-4o",
        "choices": [{"index": 0, "finish_reason": "stop", "message": message}],
    }


ANSWER = json.dumps(_completion({"role": "assistant", "content": "Your café spend was 4 USD."}), ensure_ascii=False)
CUT_MID_CHARACTER = ANSWER.encode()[: ANSWER.encode().index("é".encode()) + 1]
LATIN_1 = ANSWER.encode("latin-1")
TOO_DEEP = ANSWER[:-1].encode() + b', "extra": ' + b"[" * 100_000 + b"]" * 100_000 + b"}"
CUSTOM_TOOL = json.dumps(
    _completion(
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": "c1", "type": "custom", "custom": {"name": "run_bql_query", "input": "x"}}],
        }
    )
).encode()
BODIES = {"cut-mid-character": CUT_MID_CHARACTER, "latin-1": LATIN_1, "too-deep": TOO_DEEP, "custom-tool": CUSTOM_TOOL}
LEAKS = ("codec", "decode", "recursion", "Custom tool calls", "RuntimeError")


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(
        'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n2026-01-01 open Expenses:Food USD\n',
        encoding="utf-8",
    )
    return path


@pytest.mark.parametrize("body", BODIES.values(), ids=BODIES.keys())
def test_print_mode_says_the_reply_was_unreadable(
    tmp_path: Path, ledger: Path, stub_model: StubModel, body: bytes
) -> None:
    stub_model.reply = lambda n: body
    env = _env(tmp_path)
    env.update(BEA_TOKEN="stub-token", BEA_API_URL=stub_model.url, NO_PROXY="127.0.0.1,localhost")

    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--file", str(ledger), "ask", "--print", "What did I spend?"],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 1, result.stderr
    stderr = " ".join(result.stderr.split())
    assert "Unexpected server response (HTTP 200) from the assistant; nothing was written to your ledger." in stderr
    for leaked in LEAKS:
        assert leaked not in result.stderr, result.stderr


def test_the_session_keeps_the_write_it_already_made(
    ledger: Path, stub_model: StubModel, ask_on_a_terminal: Any
) -> None:
    directive = '2026-02-01 * "Cafe" "latte"\n  Expenses:Food  4 USD\n  Assets:Cash\n'

    def reply(number: int) -> dict[str, object] | bytes:
        if number == 1:
            return model_tool_call("write_directive", {"directive": directive})
        return CUT_MID_CHARACTER

    stub_model.reply = reply

    run = ask_on_a_terminal(
        ["--file", str(ledger), "ask"],
        [
            "add a latte",
            "@ENTER",
            "@WAIT:Append this directive to the ledger",
            "y",
            "@ENTER",
            "@WAIT:Unexpected server response",
            "@WAIT:❯",
            "@CTRL_D",
        ],
        timeout=60,
        env_overrides={"BEA_NO_ASK_HISTORY": "1"},
    )

    assert run.status == 0, run.screen
    screen = " ".join(run.screen.split())
    assert f"this question had already written 1 directive(s) to {ledger}" in screen, run.screen
    assert '"latte"' in ledger.read_text(encoding="utf-8")
    for leaked in LEAKS:
        assert leaked not in run.screen
