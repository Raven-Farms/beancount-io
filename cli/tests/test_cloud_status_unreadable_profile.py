"""A 200 profile the generated parser cannot read is an unreadable success (w5/366).

`get_user_profile`'s union parser returns the raw JSON when `from_dict`
fails, so no exception reached `call`, and `bea cloud status` printed
`'dict' object has no attribute 'username'` without the request ID.
Synthetic HTTP responses, not evidence of a live server defect.
"""

from __future__ import annotations

import json

import pytest
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from cli.main import app

PROFILE = {
    "id": 1,
    "email": "qa@example.invalid",
    "locale": "en",
    "username": "qa",
    "tier": "free",
    "limits": {"ledgersUsed": 0, "ledgersMax": 1, "collaboratorsPerLedgerMax": 1, "maxDirectives": 100},
    "hasEverSubscribed": False,
}


def _without(field: str) -> dict:
    body = json.loads(json.dumps(PROFILE))
    if field.startswith("limits."):
        del body["limits"][field.split(".", 1)[1]]
    else:
        del body[field]
    return body


@pytest.mark.parametrize("field", ["email", "locale", "limits.maxDirectives"])
@pytest.mark.parametrize("json_output", [False, True], ids=["text", "json"])
def test_a_profile_missing_a_required_field_is_an_unexpected_response(
    logged_in: None, monkeypatch: pytest.MonkeyPatch, httpx_mock: HTTPXMock, field: str, json_output: bool
) -> None:
    monkeypatch.setenv("BEA_API_URL", "https://api.example")
    httpx_mock.add_response(
        method="GET",
        url="https://api.example/api-gateway/v1/user-profile",
        json=_without(field),
        headers={"X-Request-Id": "req-qa-123"},
    )

    result = CliRunner().invoke(app, [*(["--json"] if json_output else []), "cloud", "status"])

    assert result.exit_code == 1, result.stderr
    assert result.stdout == ""
    assert "Unexpected server response (HTTP 200)." in result.stderr
    assert "has no attribute" not in result.stderr
    if json_output:
        error = json.loads(result.stderr)["error"]
        assert error["category"] == "validation"
        assert error["request_id"] == "req-qa-123"


def test_the_full_profile_still_reads(logged_in: None, monkeypatch: pytest.MonkeyPatch, httpx_mock: HTTPXMock) -> None:
    monkeypatch.setenv("BEA_API_URL", "https://api.example")
    httpx_mock.add_response(method="GET", url="https://api.example/api-gateway/v1/user-profile", json=PROFILE)

    result = CliRunner().invoke(app, ["--json", "cloud", "status"])

    assert result.exit_code == 0, result.stderr
    assert json.loads(result.stdout)["data"]["username"] == "qa"
