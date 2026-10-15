"""`create --clone` refuses an occupied target before creating the ledger (w5/371).

git refuses to clone into a file or a non-empty directory, so checking only
after the POST left the ledger on the server and the retry conflicting on its
name. The manual remedy after a real clone failure now repeats the target.
Synthetic API responses; the git remote is a local bare repository.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from cli.main import app
from tests.conftest import GitRemote


@pytest.fixture(autouse=True)
def api(logged_in: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("BEA_API_URL", "https://api.example")
    monkeypatch.chdir(tmp_path)


def _wire(ssh_url: str, name: str = "qa-new") -> dict[str, object]:
    return {
        "id": "l1",
        "name": name,
        "fullName": f"qa/{name}",
        "httpUrl": f"https://example.test/qa/{name}",
        "sshUrl": ssh_url,
        "private": True,
        "empty": True,
        "size": 0,
        "createdAt": "2026-10-02T00:00:00Z",
        "updatedAt": "2026-10-02T00:00:00Z",
    }


@pytest.mark.parametrize("json_output", [False, True], ids=["text", "json"])
@pytest.mark.parametrize("occupant", ["non-empty-dir", "file"])
def test_an_occupied_default_target_is_refused_before_the_post(
    httpx_mock: HTTPXMock, tmp_path: Path, json_output: bool, occupant: str
) -> None:
    target = tmp_path / "qa-new"
    if occupant == "file":
        target.write_text("x\n")
    else:
        target.mkdir()
        (target / "notes.txt").write_text("mine\n")

    result = CliRunner().invoke(
        app, [*(["--json"] if json_output else []), "cloud", "ledger", "create", "qa-new", "--clone"]
    )

    assert result.exit_code == 2, result.output
    assert httpx_mock.get_requests() == []
    message = json.loads(result.stderr)["error"]["message"] if json_output else result.stderr
    assert "Clone target 'qa-new' already exists and is not an empty directory; nothing was created." in message


def test_an_occupied_dir_option_is_refused_too(httpx_mock: HTTPXMock, tmp_path: Path) -> None:
    (tmp_path / "x y" / "q").mkdir(parents=True)
    (tmp_path / "x y" / "q" / "a.bean").write_text("")

    result = CliRunner().invoke(app, ["cloud", "ledger", "create", "qa-q", "--clone", "--dir", "x y/q"])

    assert result.exit_code == 2, result.output
    assert httpx_mock.get_requests() == []
    assert "Clone target 'x y/q'" in result.stderr


def test_an_empty_directory_is_still_a_valid_target(
    httpx_mock: HTTPXMock, git_remote: GitRemote, tmp_path: Path
) -> None:
    (tmp_path / "empty").mkdir()
    httpx_mock.add_response(method="POST", url="https://api.example/api-gateway/v1/ledgers", json=_wire(git_remote.url))

    result = CliRunner().invoke(app, ["cloud", "ledger", "create", "qa-new", "--clone", "--dir", "empty"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "empty" / ".git").is_dir()


def test_the_manual_remedy_repeats_the_dir_target(httpx_mock: HTTPXMock, git_remote: GitRemote) -> None:
    shutil.rmtree(git_remote.origin)
    httpx_mock.add_response(
        method="POST", url="https://api.example/api-gateway/v1/ledgers", json=_wire(git_remote.url, "qa-q")
    )

    result = CliRunner().invoke(app, ["cloud", "ledger", "create", "qa-q", "--clone", "--dir", "x y/q"])

    assert result.exit_code == 1, result.output
    assert f"Clone it manually with: git clone {git_remote.url} 'x y/q'" in result.stderr
