"""`ask` names a filtered, gzipped-labeled, or wrong-typed reply for what it is (w5/745).

1. A partial answer ending in `finish_reason: "content_filter"` printed as a
   complete answer with exit 0: `cut_off` only knew `"length"`.
2. A 200 labelled gzip but not gzipped was retried as a connection error —
   billing the question three times — then reported as "Could not reach the
   server".
3. A wrong-typed field (`"created": 1700000000.5`) printed a raw Pydantic
   warning ahead of bea's sentence.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from tests.conftest import RawReply, StubModel, model_answer
from tests.test_into_glob_create import _env

LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n'
PARTIAL = "Your January spending was 1"


def _ask(tmp_path: Path, ledger: Path, stub: StubModel) -> subprocess.CompletedProcess[str]:
    env = _env(tmp_path)
    env.update(BEA_TOKEN="stub-token", BEA_API_URL=stub.url, NO_PROXY="127.0.0.1,localhost")
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--file", str(ledger), "ask", "--print", "q"],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _envelope(choice: dict[str, object], **overrides: object) -> bytes:
    body: dict[str, object] = {
        "id": "chatcmpl-stub",
        "object": "chat.completion",
        "created": 0,
        "model": "gpt-4o",
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        "choices": [choice],
    }
    body.update(overrides)
    return json.dumps(body).encode()


def _filtered(choice_text: str = PARTIAL) -> dict[str, object]:
    choice = model_answer(choice_text)
    choice["finish_reason"] = "content_filter"
    return choice


def test_a_filtered_answer_prints_partial_with_its_own_notice(tmp_path: Path, stub_model: StubModel) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")
    stub_model.reply = lambda n: _filtered()

    result = _ask(tmp_path, ledger, stub_model)

    assert result.returncode == 1, (result.returncode, result.stdout, result.stderr)
    assert PARTIAL in result.stdout, "the partial text prints, but not as the whole answer"
    assert "content filter" in result.stderr, result.stderr
    assert "per-answer limit" not in result.stderr, "the length wording would mislead here"


def test_a_false_gzip_body_costs_one_request(tmp_path: Path, stub_model: StubModel) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")
    body = _envelope(model_answer("ok"))
    stub_model.reply = lambda n: RawReply(body=body, headers={"Content-Encoding": "gzip"})

    result = _ask(tmp_path, ledger, stub_model)

    assert stub_model.count == 1, "a body that cannot decode will not decode on retry"
    assert result.returncode == 1, (result.returncode, result.stdout, result.stderr)
    assert "Unexpected server response (HTTP 200)" in result.stderr, result.stderr
    assert "Could not reach the server" not in result.stderr, result.stderr


def test_a_wrong_typed_field_prints_only_bea_sentence(tmp_path: Path, stub_model: StubModel) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")
    stub_model.reply = lambda n: _envelope(model_answer("ok"), created=1700000000.5)

    result = _ask(tmp_path, ledger, stub_model)

    assert result.returncode == 1, (result.returncode, result.stdout, result.stderr)
    assert "Warning" not in result.stderr, result.stderr
    assert "pydantic" not in result.stderr, result.stderr
    assert result.stderr.strip().startswith("Error: "), result.stderr


def test_a_flaky_proxy_recovers_on_retry(tmp_path: Path, stub_model: StubModel) -> None:
    """Bea's own retry keeps what the SDK's default gave: one blip, no failure.

    This passes before the fix too (the SDK retried); it pins that the move of
    retries into bea's model wrapper loses nothing.
    """
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")

    def reply(n: int) -> object:
        if n == 1:
            return (500, {"message": "upstream boom"})
        return model_answer("recovered")

    stub_model.reply = reply

    result = _ask(tmp_path, ledger, stub_model)

    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    assert "recovered" in result.stdout
    assert stub_model.count == 2, "the blip retried once, then answered"


def test_a_server_refusal_to_retry_is_obeyed(tmp_path: Path, stub_model: StubModel) -> None:
    """`x-should-retry: false` still means one attempt, as the client's own retries read it."""
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")
    body = json.dumps({"message": "do not try again"}).encode()
    stub_model.reply = lambda n: RawReply(body=body, headers={"x-should-retry": "false"}, status=500)

    result = _ask(tmp_path, ledger, stub_model)

    assert stub_model.count == 1, result.stderr
    assert result.returncode == 1, (result.returncode, result.stdout, result.stderr)
    assert "Server error" in result.stderr, result.stderr


def test_a_filtered_answer_in_a_session_names_the_filter(
    tmp_path: Path, stub_model: StubModel, ask_on_a_terminal: Any
) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")
    stub_model.reply = lambda n: _filtered()

    run = ask_on_a_terminal(
        ["--file", str(ledger), "ask"],
        ["q", "@ENTER", "@WAIT:❯", "@CTRL_D"],
    )

    assert run.status == 0, run.screen
    assert PARTIAL in run.screen, run.screen
    assert "content filter" in run.screen, run.screen
