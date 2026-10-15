"""A cloud write answered with a success bea cannot read has an unknown outcome (w5/422).

`cloud ledger create`/`delete` reported an unreadable or empty 2xx with the
read error ("Empty response (HTTP 201)", exit 1), so the user was not told
the server most likely applied the write, and the natural retry hit 409 or
404. Server responses are simulated with pytest-httpx.
"""

from __future__ import annotations

import json

import pytest
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from cli.main import app
from tests.test_cloud_create_json_parity import _API, _WIRE

UNKNOWN = "but the response could not be read. It most likely took effect, but the outcome is unknown"


@pytest.fixture(autouse=True)
def _cloud(logged_in: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BEA_API_URL", _API)


@pytest.mark.parametrize(
    ("status", "body"),
    [(201, json.dumps(_WIRE).encode()), (200, b"{}"), (200, b"null"), (204, b"")],
    ids=["201-valid", "200-empty-object", "200-null", "204"],
)
@pytest.mark.parametrize("json_output", [False, True])
def test_create(httpx_mock: HTTPXMock, status: int, body: bytes, json_output: bool) -> None:
    httpx_mock.add_response(method="POST", url=f"{_API}/api-gateway/v1/ledgers", status_code=status, content=body)

    result = CliRunner().invoke(app, [*(["--json"] if json_output else []), "cloud", "ledger", "create", "new2"])

    assert result.exit_code == 4, result.output
    assert f"Creating ledger 'new2' was answered with HTTP {status}, {UNKNOWN}" in result.stderr
    if json_output:
        assert json.loads(result.stderr)["error"]["category"] == "conflict"


def test_delete(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="DELETE", url=f"{_API}/api-gateway/v1/ledgers/qa/one", status_code=200, content=b"{}"
    )

    result = CliRunner().invoke(app, ["--yes", "cloud", "ledger", "delete", "qa/one"])

    assert result.exit_code == 4, result.output
    assert f"Deleting ledger 'qa/one' was answered with HTTP 200, {UNKNOWN}" in result.stderr


def test_a_readable_create_still_succeeds(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="POST", url=f"{_API}/api-gateway/v1/ledgers", json=_WIRE)
    assert CliRunner().invoke(app, ["cloud", "ledger", "create", "new2"]).exit_code == 0
