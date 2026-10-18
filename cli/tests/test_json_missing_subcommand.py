"""Bare groups give JSON callers usable choices instead of a help page (w5/680)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import typer
import typer.main
from typer.testing import CliRunner

from cli.commands.add import add_app
from cli.main import app

ROOT = Path(__file__).resolve().parents[1]
GROUPS = [("add",), ("list",), ("report",), ("cloud",), ("cloud", "ledger"), ("doctor",), ("engine",), ("ingest",)]


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("BEA_") and key != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _visible_choices(path: tuple[str, ...]) -> list[str]:
    command = typer.main.get_command(app)
    ctx = typer.Context(command, info_name="bea")
    for name in path:
        command = command.get_command(ctx, name)
        ctx = typer.Context(command, info_name=name, parent=ctx)
    return [
        name
        for name in command.list_commands(ctx)
        if (child := command.get_command(ctx, name)) is not None and not child.hidden
    ]


@pytest.mark.parametrize("group", GROUPS, ids=lambda group: "-".join(group))
def test_json_bare_group_names_exactly_its_visible_subcommands(tmp_path: Path, group: tuple[str, ...]) -> None:
    result = _bea(tmp_path, "--json", *group)

    assert result.returncode == 2, result.stdout + result.stderr
    assert result.stdout == ""
    error = json.loads(result.stderr)["error"]
    assert error["category"] == "usage" and error["exit_code"] == 2, error
    message = error["message"]
    prefix = "Missing subcommand: choose one of "
    assert message.startswith(prefix) and message.endswith("."), message
    assert "\n" not in message and "Usage:" not in message, message
    assert message.removeprefix(prefix).removesuffix(".").split(", ") == _visible_choices(group)


@pytest.mark.parametrize("group", [("add",), ("cloud", "ledger"), ("doctor",), ("ingest",)])
def test_human_bare_group_keeps_its_help_page(tmp_path: Path, group: tuple[str, ...]) -> None:
    result = _bea(tmp_path, *group)

    assert result.returncode == 2, result.stdout + result.stderr
    shown = result.stdout + result.stderr
    assert "Usage:" in shown and "Commands:" in shown, shown
    assert "Missing subcommand:" not in shown


@pytest.mark.parametrize("json_output", [False, True], ids=["human", "json-flag"])
@pytest.mark.parametrize("group", [("add",), ("cloud", "ledger"), ("report",)])
def test_explicit_group_help_still_succeeds(tmp_path: Path, json_output: bool, group: tuple[str, ...]) -> None:
    result = _bea(tmp_path, *(["--json"] if json_output else []), *group, "--help")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Usage:" in result.stdout and "Commands:" in result.stdout
    assert result.stderr == ""


def test_json_root_without_command_keeps_the_existing_message(tmp_path: Path) -> None:
    result = _bea(tmp_path, "--json")

    assert result.returncode == 2, result.stdout + result.stderr
    assert result.stdout == ""
    assert json.loads(result.stderr)["error"] == {"category": "usage", "message": "Missing command.", "exit_code": 2}


def test_hidden_subcommands_are_accepted_but_never_suggested(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(add_app, "registered_commands", list(add_app.registered_commands))

    @add_app.command("internal-probe", hidden=True)
    def internal_probe() -> None:
        pass

    runner = CliRunner()
    missing = runner.invoke(app, ["--json", "add"])

    assert missing.exit_code == 2, missing.output
    message = json.loads(missing.stderr)["error"]["message"]
    assert message.startswith("Missing subcommand: choose one of ")
    assert "internal-probe" not in message
    assert runner.invoke(app, ["add", "internal-probe"]).exit_code == 0
