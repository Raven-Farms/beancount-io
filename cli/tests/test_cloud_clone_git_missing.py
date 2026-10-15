"""`cloud ledger clone` with no git refuses before any request, as `create --clone` does (w5/372).

It fetched the ledger first and then reported the OSError from starting git,
exit 1. Synthetic API: no response is registered, so any request would show.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from cli.main import app


@pytest.mark.parametrize("json_output", [False, True], ids=["text", "json"])
@pytest.mark.parametrize(
    ("command", "use"),
    [
        (["cloud", "ledger", "clone", "qa/book"], "bea cloud ledger clone"),
        (["cloud", "ledger", "create", "qa-z", "--clone"], "--clone"),
    ],
    ids=["clone", "create-clone"],
)
def test_missing_git_is_a_usage_error_before_any_request(
    logged_in: None,
    monkeypatch: pytest.MonkeyPatch,
    httpx_mock: HTTPXMock,
    tmp_path: Path,
    json_output: bool,
    command: list[str],
    use: str,
) -> None:
    monkeypatch.setenv("BEA_API_URL", "https://api.example")
    empty = tmp_path / "no-git"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))

    result = CliRunner().invoke(app, [*(["--json"] if json_output else []), *command])

    assert result.exit_code == 2, result.output
    assert httpx_mock.get_requests() == []
    message = json.loads(result.stderr)["error"]["message"] if json_output else result.stderr
    assert f"git executable not found on PATH; install Git before using {use}" in message
    assert "could not start git" not in result.stderr
