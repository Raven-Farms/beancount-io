"""A write the user cannot approve is skipped before it is validated (w5/848).

`--print` ran the dry run first and sent the model its outcome: a `document`
for a missing file came back "File does not exist", an existing one "Write
skipped" — one bit of filesystem existence per call, unseen by anyone. In an
interactive session a rejection now reaches the user as well as the model.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.ask.agent import BqlDeps, WritePermission, make_agent
from cli.main import app
from tests.conftest import StubModel, model_answer, model_tool_call

runner = CliRunner()
SKIPPED = "Write skipped (non-interactive mode does not support writes)."
LEDGER = "2024-01-01 open Assets:Cash USD\n"


@pytest.mark.parametrize("path", ["/etc/hosts", "/nonexistent/qa/file.pdf"])
def test_print_tells_the_model_the_same_thing_whatever_the_path(
    tmp_path: Path, stub_model: StubModel, monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    directive = f'2024-01-20 document Assets:Cash "{path}"'
    stub_model.reply = lambda n: (
        model_tool_call("write_directive", {"directive": directive}) if n == 1 else model_answer("Done.")
    )
    monkeypatch.setenv("BEA_TOKEN", "stub-token")
    monkeypatch.setenv("BEA_API_URL", stub_model.url)

    result = runner.invoke(app, ["--file", str(ledger), "ask", "--print", "add it"], input="")

    assert result.exit_code == 0, result.output
    tool_messages = [m for m in stub_model.requests[1]["messages"] if m.get("role") == "tool"]  # type: ignore[union-attr]
    assert [message["content"] for message in tool_messages] == [SKIPPED]
    assert str(tmp_path) not in json.dumps(stub_model.requests[1])
    assert ledger.read_text() == LEDGER


def test_no_dry_run_runs_without_a_way_to_approve(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from cli.ask import agent as agent_module

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("the dry run must not run")

    monkeypatch.setattr(agent_module.launch, "helper_json", forbidden)
    deps = BqlDeps(file=tmp_path / "main.bean", write_permission=WritePermission())
    write = make_agent("gpt-4o", "http://unused", "tok")._function_toolset.tools["write_directive"].function

    assert write(SimpleNamespace(deps=deps), '2024-01-20 document Assets:Cash "/etc/hosts"') == SKIPPED


@pytest.mark.parametrize("path", ["/etc/hosts", "/nonexistent/qa/file.pdf"])
def test_an_interactive_document_outside_the_folder_is_refused_alike(tmp_path: Path, path: str) -> None:
    """Outside the ledger's folder, existing and missing files get one answer, and no panel."""
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    asked: list[str] = []
    deps = BqlDeps(
        file=ledger, write_permission=WritePermission(confirm_fn=lambda d, t, w, p: (asked.append(d), "n")[1])
    )
    write = make_agent("gpt-4o", "http://unused", "tok")._function_toolset.tools["write_directive"].function

    answer = write(SimpleNamespace(deps=deps), f'2024-01-20 document Assets:Cash "{path}"')

    assert answer == (
        "Write rejected: an AI-proposed document must name a file inside the ledger's folder; "
        "this one is outside it. Move the file into the ledger's folder first."
    )
    assert asked == []
    assert ledger.read_text() == LEDGER


def test_a_document_inside_the_folder_still_reaches_the_panel(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    (tmp_path / "receipt.pdf").write_bytes(b"%PDF")
    asked: list[str] = []
    deps = BqlDeps(
        file=ledger, write_permission=WritePermission(confirm_fn=lambda d, t, w, p: (asked.append(d), "n")[1])
    )
    write = make_agent("gpt-4o", "http://unused", "tok")._function_toolset.tools["write_directive"].function

    answer = write(SimpleNamespace(deps=deps), '2024-01-20 document Assets:Cash "receipt.pdf"')

    assert answer == "Write cancelled by user."
    assert len(asked) == 1
