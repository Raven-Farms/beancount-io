"""A cloud write that never connected says so instead of "outcome unknown" (w5/368).

`cloud ledger create`/`delete` sent every httpx transport error to the
unknown-outcome path (exit 4), including a refused connection or a failed
lookup, where no request left the machine. Those now read like any other
unreachable server (exit 1); a timeout after the request was sent stays 4.
Synthetic transport failures, not evidence of a live server defect.
"""

from __future__ import annotations

import json

import httpx
import pytest
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from cli.main import app

WRITES = {
    "create": ["cloud", "ledger", "create", "qa-z"],
    "delete": ["--yes", "cloud", "ledger", "delete", "alice/books"],
}


@pytest.fixture
def api(logged_in: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BEA_API_URL", "https://api.example")


@pytest.mark.parametrize("write", sorted(WRITES))
@pytest.mark.parametrize(
    "failure",
    [httpx.ConnectError("Connection refused"), httpx.ConnectTimeout("connect timed out")],
    ids=["refused", "connect-timeout"],
)
def test_a_write_that_never_connected_could_not_reach_the_server(
    api: None, httpx_mock: HTTPXMock, write: str, failure: Exception
) -> None:
    httpx_mock.add_exception(failure)

    result = CliRunner().invoke(app, ["--json", *WRITES[write]])

    assert result.exit_code == 1, result.stderr
    error = json.loads(result.stderr)["error"]
    assert error["message"] == f"Could not reach the server ({type(failure).__name__})."
    assert "outcome is unknown" not in result.stderr


@pytest.mark.parametrize("write", sorted(WRITES))
def test_a_write_that_timed_out_after_sending_is_still_unknown(api: None, httpx_mock: HTTPXMock, write: str) -> None:
    httpx_mock.add_exception(httpx.ReadTimeout("read timed out"))

    result = CliRunner().invoke(app, ["--json", *WRITES[write]])

    assert result.exit_code == 4, result.stderr
    assert "The outcome is unknown" in json.loads(result.stderr)["error"]["message"]
