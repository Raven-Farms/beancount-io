"""A redirect or an unexpected empty status is not a rejected credential (w5/367).

`unwrap_or_none` returned `None` for any status below 400 the generated
parser skipped, and `cloud status` reads `None` as a revoked bearer, so a
302 from an https-only API or a proxy exited 3 telling the user to log in
again. Synthetic HTTP responses, not evidence of a live server defect.
"""

from __future__ import annotations

import json

import pytest
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from cli.main import app

PROFILE_URL = "https://api.example/api-gateway/v1/user-profile"


@pytest.fixture
def api(logged_in: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BEA_API_URL", "https://api.example")


def _status(json_output: bool) -> tuple[int, str, dict | None]:
    result = CliRunner().invoke(app, [*(["--json"] if json_output else []), "cloud", "status"])
    error = json.loads(result.stderr)["error"] if json_output else None
    return result.exit_code, result.stderr, error


@pytest.mark.parametrize("json_output", [False, True], ids=["text", "json"])
def test_a_redirect_is_named_not_blamed_on_the_credential(api: None, httpx_mock: HTTPXMock, json_output: bool) -> None:
    httpx_mock.add_response(
        url=PROFILE_URL,
        status_code=302,
        headers={"Location": "https://portal.example/login?session=s3cret", "X-Request-Id": "req-qa-302"},
    )

    code, stderr, error = _status(json_output)

    assert code == 1, stderr
    assert "Unexpected redirect (HTTP 302) to https://portal.example/login;" in stderr
    assert "BEA_API_URL" in stderr
    assert "s3cret" not in stderr
    assert "bea cloud login" not in stderr
    assert "mint a new token" not in stderr
    if error is not None:
        assert error["category"] == "validation"
        assert error["request_id"] == "req-qa-302"


def test_a_redirect_on_another_command_is_named_too(api: None, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=307, headers={"Location": "http://api.example/api-gateway/v1/ledgers"})

    result = CliRunner().invoke(app, ["cloud", "ledger", "list"])

    assert result.exit_code == 1, result.stderr
    assert "Unexpected redirect (HTTP 307) to http://api.example/api-gateway/v1/ledgers;" in result.stderr
    assert "Empty response" not in result.stderr


def test_a_204_profile_is_an_unexpected_response(api: None, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=PROFILE_URL, status_code=204, headers={"X-Request-Id": "req-qa-204"})

    code, stderr, error = _status(True)

    assert code == 1, stderr
    assert error is not None
    assert error["message"] == "Unexpected server response (HTTP 204)."
    assert error["request_id"] == "req-qa-204"


def test_a_null_200_profile_is_still_a_rejected_credential(api: None, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=PROFILE_URL, status_code=200, content=b"null")

    code, stderr, error = _status(True)

    assert code == 3, stderr
    assert error is not None
    assert error["category"] == "auth"
