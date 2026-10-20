"""A ledger under an unsearchable directory is refused by name, never as a raw OS error (w5/793).

`Path.exists` and friends raise `PermissionError` on EACCES, so `check`
exited 1 with a raw `[Errno 13]` and `init` did the same. Reads now exit 2
with the unreadable-ledger wording; init exits 3 through the engine's
creation check, as for a read-only parent (w5/090).
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

pytestmark = pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="needs POSIX permissions that bind the current user",
)


@pytest.fixture
def work(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bea_config_dir: Path) -> Iterator[Path]:
    directory = tmp_path / "work"
    (directory / "locked").mkdir(parents=True)
    (directory / "locked" / "main.bean").write_text('option "operating_currency" "USD"\n2026-01-01 open Assets:A USD\n')
    (directory / "locked").chmod(0o000)
    monkeypatch.chdir(directory)
    yield directory
    (directory / "locked").chmod(0o755)


def _run(*args: str, as_json: bool = False) -> Any:
    return runner.invoke(app, [*(["--json"] if as_json else []), "--no-input", *args])


def _clean(result: Any) -> str:
    text = " ".join(result.output.split())
    for raw in ("Errno", "PermissionError", "Traceback"):
        assert raw not in text, text
    return text


def _tree(work: Path) -> list[str]:
    (work / "locked").chmod(0o755)
    try:
        return sorted(str(path.relative_to(work)) for path in work.rglob("*"))
    finally:
        (work / "locked").chmod(0o000)


def test_check_names_the_unreadable_ledger(work: Path) -> None:
    result = _run("-f", "locked/main.bean", "check")

    assert result.exit_code == 2, result.output
    text = _clean(result)
    assert "Ledger path 'locked/main.bean' (from --file) is not readable." in text


def test_json_balance_carries_usage(work: Path) -> None:
    result = _run("-f", "locked/main.bean", "balance", as_json=True)

    assert result.exit_code == 2, result.output
    error = json.loads(result.stderr)["error"]
    assert (error["category"], error["exit_code"]) == ("usage", 2)
    assert "locked/main.bean" in error["message"]


@pytest.mark.parametrize(
    "args",
    [["init", "locked/books", "--currency", "USD"], ["init", "locked/sub/books", "--currency", "USD"]],
    ids=["shallow", "deep"],
)
def test_init_under_an_unsearchable_directory_exits_3(work: Path, args: list[str]) -> None:
    before = _tree(work)

    result = _run(*args)

    assert result.exit_code == 3, result.output
    text = _clean(result)
    assert "locked" in text
    assert "Nothing was written" in text
    assert _tree(work) == before


def test_init_file_target_under_an_unsearchable_directory_exits_3(work: Path) -> None:
    result = _run("--file", "locked/main.bean", "init", "--currency", "USD")

    assert result.exit_code == 3, result.output
    text = _clean(result)
    assert "locked" in text
    assert "Nothing was written" in text


def test_init_json_carries_auth(work: Path) -> None:
    result = _run("init", "locked/books", "--currency", "USD", as_json=True)

    assert result.exit_code == 3, result.output
    error = json.loads(result.stderr)["error"]
    assert (error["category"], error["exit_code"]) == ("auth", 3)
    assert "locked" in error["message"]


def test_unreadable_file_keeps_its_refusal(work: Path, tmp_path: Path) -> None:
    (work / "locked").chmod(0o755)
    (work / "locked" / "main.bean").chmod(0o000)
    try:
        result = _run("-f", "locked/main.bean", "check")
    finally:
        (work / "locked" / "main.bean").chmod(0o644)
        (work / "locked").chmod(0o000)

    assert result.exit_code == 2, result.output
    assert "Path 'locked/main.bean' is not readable." in _clean(result)
