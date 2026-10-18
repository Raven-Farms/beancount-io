"""Generated cloud paging validates the spec's bounds before auth or HTTP (w5/680)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import typer
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from cli.main import _GuardedGroup, app

ROOT = Path(__file__).resolve().parents[1]
URL = "https://api.example/api-gateway/v1/ledgers"
runner = CliRunner()
INVALID = [("--limit", "0"), ("--limit", "-3"), ("--limit", "101"), ("--page", "0"), ("--page", "-1")]


@pytest.mark.parametrize("json_output", [False, True], ids=["human", "json"])
@pytest.mark.parametrize(("option", "value"), INVALID)
def test_invalid_paging_is_usage_before_credentials_or_http(
    monkeypatch: pytest.MonkeyPatch, httpx_mock: HTTPXMock, json_output: bool, option: str, value: str
) -> None:
    def credentials_must_not_be_read() -> None:
        pytest.fail("invalid paging reached credential resolution")

    monkeypatch.setattr("cli.api.client.authenticated_client", credentials_must_not_be_read)

    result = runner.invoke(app, [*(["--json"] if json_output else []), "cloud", "ledger", "list", option, value])

    assert result.exit_code == 2, result.output
    assert result.stdout == ""
    if json_output:
        error = json.loads(result.stderr)["error"]
        assert error["category"] == "usage" and error["exit_code"] == 2, error
        message = error["message"]
    else:
        message = result.stderr
    assert option in message and "range" in message, message
    assert "Not logged in" not in message
    assert httpx_mock.get_requests() == []


@pytest.mark.parametrize(("page", "limit"), [(1, 1), (1, 100), (987, 50)])
def test_valid_bounds_reach_the_server_with_unchanged_values(
    monkeypatch: pytest.MonkeyPatch, logged_in: None, httpx_mock: HTTPXMock, page: int, limit: int
) -> None:
    monkeypatch.setenv("BEA_API_URL", "https://api.example")
    httpx_mock.add_response(url=f"{URL}?page={page}&limit={limit}", json=[])

    result = runner.invoke(app, ["--json", "cloud", "ledger", "list", "--page", str(page), "--limit", str(limit)])

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["data"] == []
    [request] = httpx_mock.get_requests()
    assert request.url.params["page"] == str(page) and request.url.params["limit"] == str(limit)


def test_generated_bounds_follow_changed_schema_values_instead_of_hardcoded_paging(tmp_path: Path) -> None:
    spec = json.loads((ROOT / "openapi" / "v1.json").read_text())
    parameters = spec["paths"]["/api-gateway/v1/ledgers"]["get"]["parameters"]
    for parameter in parameters:
        if parameter["name"] == "page":
            parameter["schema"]["minimum"] = 2
        if parameter["name"] == "limit":
            parameter["schema"]["minimum"] = 2
            parameter["schema"]["maximum"] = 7
    scratch = tmp_path / "spec.json"
    scratch.write_text(json.dumps(spec))
    generated = tmp_path / "generated"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "gen_cloud_commands.py"),
            "--spec",
            str(scratch),
            "--out",
            str(generated),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    namespace: dict[str, Any] = {"__name__": "test_generated_cloud_bounds"}
    source = (generated / "ledger.py").read_text()
    exec(compile(source, str(generated / "ledger.py"), "exec"), namespace)
    generated_app = typer.Typer(cls=_GuardedGroup, no_args_is_help=True, rich_markup_mode=None)
    namespace["register_ledger_commands"](generated_app)

    for option, value in [("--page", "1"), ("--limit", "1"), ("--limit", "8")]:
        values = {"--page": "2", "--limit": "2", option: value}
        args = [part for pair in values.items() for part in pair]
        refused = runner.invoke(generated_app, ["list", *args])
        assert refused.exit_code == 2 and "range" in refused.stderr, refused.output
    for limit in (2, 7):
        valid = runner.invoke(generated_app, ["list", "--page", "2", "--limit", str(limit)])
        assert valid.exit_code == 3 and "Not logged in" in valid.stderr, valid.output
