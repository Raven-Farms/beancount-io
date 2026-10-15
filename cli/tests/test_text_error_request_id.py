"""A text-mode cloud error shows the backend request ID that `--json` keeps (w5/369).

Synthetic HTTP responses, not evidence of a live server defect.
"""

from __future__ import annotations

import json

import pytest
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from cli.main import app


@pytest.fixture
def api(logged_in: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BEA_API_URL", "https://api.example")


def _server_error(httpx_mock: HTTPXMock, headers: dict[str, str]) -> None:
    httpx_mock.add_response(
        status_code=500,
        json={"ok": False, "error": {"code": "INTERNAL", "message": "mock 500 message"}},
        headers=headers,
    )


@pytest.mark.parametrize(("status", "exit_code"), [(500, 1), (401, 3), (404, 1)])
def test_text_mode_prints_the_request_id(api: None, httpx_mock: HTTPXMock, status: int, exit_code: int) -> None:
    httpx_mock.add_response(
        status_code=status,
        json={"ok": False, "error": {"code": "SOME_CODE", "message": "the server's own words"}},
        headers={"X-Request-Id": "req-qa-123"},
    )

    result = CliRunner().invoke(app, ["cloud", "ledger", "list"])

    assert result.exit_code == exit_code, result.stderr
    lines = result.stderr.splitlines()
    assert lines[0].startswith("Error: ") and "the server's own words" in lines[0]
    assert "  Request ID: req-qa-123" in lines


def test_json_mode_is_unchanged(api: None, httpx_mock: HTTPXMock) -> None:
    _server_error(httpx_mock, {"X-Request-Id": "req-qa-123"})

    result = CliRunner().invoke(app, ["--json", "cloud", "ledger", "list"])

    assert result.exit_code == 1
    error = json.loads(result.stderr)["error"]
    assert error["request_id"] == "req-qa-123"
    assert "Request ID" not in error["message"]


def test_an_error_without_a_request_id_prints_no_such_line(api: None, httpx_mock: HTTPXMock) -> None:
    _server_error(httpx_mock, {})

    result = CliRunner().invoke(app, ["cloud", "ledger", "list"])

    assert result.exit_code == 1
    assert "Server error (mock 500 message)." in result.stderr
    assert "Request ID" not in result.stderr


def test_a_request_id_is_made_inert(api: None, httpx_mock: HTTPXMock) -> None:
    _server_error(httpx_mock, {"X-Request-Id": "req\x1b[31m-red"})

    result = CliRunner().invoke(app, ["cloud", "ledger", "list"])

    assert "\x1b" not in result.stderr
    assert "Request ID: req" in result.stderr
