"""The BQL tool hands the model the engine's details, and never blames a valid ledger (w5/549).

A failed query came back as `BQL error: … not found in table "postings"..`,
without the caret or the column list that make it fixable, and an engine
crash, such as an empty query, as `Ledger is invalid: IndexError: …`, which
pushed the model to "fix" a ledger that loads.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from cli.errors import LedgerError
from tests.conftest import StubModel, model_answer, model_tool_call
from tests.test_into_glob_create import _env

LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n'


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
        timeout=60,
    )


def _tool_results(stub: StubModel, request: int) -> list[str]:
    messages = stub.requests[request].get("messages") or []
    return [str(message.get("content")) for message in messages if message.get("role") == "tool"]  # type: ignore[union-attr]


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(LEDGER, encoding="utf-8")
    return path


def test_the_model_reads_the_column_list_and_a_blank_query_refusal(
    tmp_path: Path, ledger: Path, stub_model: StubModel
) -> None:
    calls = {1: {"query": "SELECT foo"}, 2: {"query": ""}}
    stub_model.reply = lambda n: (
        model_tool_call("run_bql_query", calls[n], f"c{n}") if n in calls else model_answer("ok")
    )

    result = _ask(tmp_path, ledger, stub_model)

    assert result.returncode == 0, result.stderr
    first = _tool_results(stub_model, 1)[-1]
    assert 'BQL error: Cannot run this BQL query: column "foo" not found in table "postings".\n' in first
    assert "\n  SELECT foo\n         ^\n" in first
    assert "Columns in postings: account, " in first
    assert ".." not in first and "bea query .tables" not in first and "--debug" not in first
    second = _tool_results(stub_model, 2)[-1]
    assert "The query is empty. Send a BQL SELECT statement." in second
    assert "Ledger is invalid" not in second and "IndexError" not in second


def test_an_engine_crash_is_not_an_invalid_ledger() -> None:
    from cli.ask.agent import _query_failure

    crash = LedgerError("IndexError: list index out of range. Pass --debug before the command for a traceback.")
    crash.traceback = "Traceback (most recent call last): ..."

    assert _query_failure(crash) == (
        "The query engine failed on this query (IndexError: list index out of range); the ledger is not at fault. "
        "Rephrase the query and retry."
    )


def test_an_invalid_ledger_is_still_named(tmp_path: Path, stub_model: StubModel) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER + '2026-02-01 * "x"\n  Assets:Cash  1 USD\n  Expenses:Nope\n', encoding="utf-8")
    calls = {1: {"query": "SELECT account"}}
    stub_model.reply = lambda n: model_tool_call("run_bql_query", calls[n], "c1") if n in calls else model_answer("ok")

    result = _ask(tmp_path, ledger, stub_model)

    assert result.returncode == 0, result.stderr
    assert "Ledger is invalid: " in _tool_results(stub_model, 1)[-1]
