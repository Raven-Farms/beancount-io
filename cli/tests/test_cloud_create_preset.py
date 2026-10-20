"""`cloud ledger create --preset` sends the setup spec and a requestId (w3/m53/t004)."""

from __future__ import annotations

import json

import pytest
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from cli.main import app

_API = "https://api.example"
_WIRE = {
    "id": "ledger-2",
    "name": "new2",
    "fullName": "alice/new2",
    "description": None,
    "httpUrl": "https://example.test/alice/new2",
    "sshUrl": "git@example.test:alice/new2.git",
    "private": True,
    "empty": True,
    "size": 0,
    "createdAt": "2026-10-03T00:00:00Z",
    "updatedAt": "2026-10-03T00:00:00Z",
}


@pytest.fixture(autouse=True)
def _cloud(logged_in: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BEA_API_URL", _API)


def test_create_with_preset_sends_setup_and_request_id(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="POST", url=f"{_API}/api-gateway/v1/ledgers", json=_WIRE)
    result = CliRunner().invoke(
        app,
        [
            "--json",
            "cloud",
            "ledger",
            "create",
            "new2",
            "--preset",
            "personal@1",
            "--currency",
            "EUR",
            "--date",
            "2026-02-01",
        ],
    )
    assert result.exit_code == 0, result.output
    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["setup"]["preset"] == "personal@1"
    assert body["setup"]["operatingCurrency"] == "EUR"
    assert body["setup"]["historyStart"] == "2026-02-01"
    assert body["requestId"]


def test_create_without_preset_sends_request_id_only(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="POST", url=f"{_API}/api-gateway/v1/ledgers", json=_WIRE)
    result = CliRunner().invoke(app, ["--json", "cloud", "ledger", "create", "new2"])
    assert result.exit_code == 0, result.output
    body = json.loads(httpx_mock.get_requests()[0].content)
    assert "setup" not in body or body["setup"] is None
    assert body["requestId"]


def test_create_rejects_unknown_preset_before_any_request(httpx_mock: HTTPXMock) -> None:
    result = CliRunner().invoke(app, ["--json", "cloud", "ledger", "create", "new2", "--preset", "nope@1"])
    assert result.exit_code != 0
    assert httpx_mock.get_requests() == []
