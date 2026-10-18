"""`cloud ledger clone` refuses an occupied target before git, as `create --clone` does (w5/520).

`clone --dir target` into a non-empty directory asked the server first and
then exited 1 with git's message; `create --clone` refuses the same target
with exit 2 before any request. Synthetic API responses.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from cli.main import app


@pytest.fixture(autouse=True)
def api(logged_in: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("BEA_API_URL", "https://api.example")
    monkeypatch.chdir(tmp_path)


def _wire(name: str = "books") -> dict[str, object]:
    return {
        "id": "l1",
        "name": name,
        "fullName": f"qa/{name}",
        "httpUrl": f"https://example.test/qa/{name}",
        "sshUrl": f"git@example.test:qa/{name}.git",
        "private": True,
        "empty": False,
        "size": 1,
        "createdAt": "2026-10-02T00:00:00Z",
        "updatedAt": "2026-10-02T00:00:00Z",
        "description": "",
        "permissions": {"admin": True, "pull": True, "push": True},
    }


@pytest.mark.parametrize("json_output", [False, True], ids=["text", "json"])
def test_an_occupied_dir_option_is_refused_before_any_request(
    httpx_mock: HTTPXMock, tmp_path: Path, json_output: bool
) -> None:
    (tmp_path / "target").mkdir()
    (tmp_path / "target" / "notes.txt").write_text("mine\n")

    result = CliRunner().invoke(
        app, [*(["--json"] if json_output else []), "cloud", "ledger", "clone", "qa/books", "--dir", "target"]
    )

    assert result.exit_code == 2, result.output
    assert httpx_mock.get_requests() == []
    message = json.loads(result.stderr)["error"]["message"] if json_output else result.stderr
    assert "Clone target 'target' already exists and is not an empty directory; nothing was cloned." in message


def test_an_occupied_default_target_is_refused_after_the_lookup(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    (tmp_path / "books").mkdir()
    (tmp_path / "books" / "notes.txt").write_text("mine\n")
    httpx_mock.add_response(method="GET", url="https://api.example/api-gateway/v1/ledgers/qa/books", json=_wire())

    result = CliRunner().invoke(app, ["cloud", "ledger", "clone", "qa/books"])

    assert result.exit_code == 2, result.output
    assert len(httpx_mock.get_requests()) == 1
    assert "books' already exists and is not an empty directory; nothing was cloned." in result.stderr
    assert "fatal:" not in result.stderr
    assert (tmp_path / "books" / "notes.txt").read_text() == "mine\n"
