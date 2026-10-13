"""`query -o` to a place the filesystem refuses ends the same way with and without `--json` (w5/119).

Text mode is written by the engine and `--json` by the frontend, and the two
disagreed: a read-only directory was exit 3 in text and a `validation` exit 1
naming a hidden `.bea-*.tmp` staging file under `--json`, and a read-only
existing file was refused under `--json` but silently replaced in text.
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

from cli.engine import launch
from cli.errors import AuthError
from cli.main import app
from cli.utils import atomic_write

runner = CliRunner()

pytestmark = pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="needs POSIX permissions that bind the current user",
)

LEDGER = """2026-01-01 open Assets:A
2026-01-01 open Equity:B
2026-01-02 * "Seed"
  Assets:A   1 USD
  Equity:B  -1 USD
"""

MODES = pytest.mark.parametrize("as_json", [False, True], ids=["text", "json"])


@pytest.fixture
def books(tmp_path: Path, bea_config_dir: Path) -> Iterator[Path]:
    directory = tmp_path / "books"
    (directory / "lock").mkdir(parents=True)
    (directory / "a.bean").write_text(LEDGER)
    (directory / "lock" / "old.txt").write_text("old")
    (directory / "keep.txt").write_text("old")
    (directory / "keep.txt").chmod(0o444)
    (directory / "lock").chmod(0o555)
    yield directory
    (directory / "lock").chmod(0o755)
    (directory / "keep.txt").chmod(0o644)


def _query(books: Path, destination: Path, *, as_json: bool) -> Any:
    return runner.invoke(
        app,
        [*(["--json"] if as_json else []), "--no-input", "-f", str(books / "a.bean"), "query", "SELECT account"]
        + ["-o", str(destination)],
    )


def _refused(result: Any, as_json: bool, named: Path) -> None:
    """Exit 3 in the permission category, naming the destination and no staging file."""
    assert result.exit_code == 3, result.output
    assert result.stdout == ""
    message = " ".join(result.stderr.split())
    if as_json:
        error = json.loads(result.stderr)["error"]
        assert (error["category"], error["exit_code"]) == ("auth", 3)
        message = error["message"]
    for raw in ("Errno", "PermissionError", "Traceback", ".bea-"):
        assert raw not in message, message
    assert str(named) in message
    assert "Nothing was written" in message


def _tree(books: Path) -> list[str]:
    return sorted(str(path.relative_to(books)) for path in books.rglob("*"))


@MODES
def test_a_new_file_in_a_read_only_directory_is_a_permission_refusal(books: Path, as_json: bool) -> None:
    before = _tree(books)

    result = _query(books, books / "lock" / "out.txt", as_json=as_json)

    _refused(result, as_json, books / "lock" / "out.txt")
    assert _tree(books) == before


@MODES
def test_an_existing_file_in_a_read_only_directory_is_a_permission_refusal(books: Path, as_json: bool) -> None:
    """The file itself is writable, so only the writer's own staging step meets the refusal."""
    before = _tree(books)

    result = _query(books, books / "lock" / "old.txt", as_json=as_json)

    _refused(result, as_json, books / "lock")
    assert (books / "lock" / "old.txt").read_text() == "old"
    assert _tree(books) == before


@MODES
def test_a_read_only_file_is_refused_and_kept(books: Path, as_json: bool) -> None:
    keep = books / "keep.txt"

    result = _query(books, keep, as_json=as_json)

    _refused(result, as_json, keep)
    assert keep.read_text() == "old"
    assert keep.stat().st_mode & 0o777 == 0o444


def test_the_engine_refuses_a_read_only_export_on_its_own(books: Path) -> None:
    """Text mode's writer holds the rule too, not only the frontend check in front of it."""
    keep = books / "keep.txt"

    with pytest.raises(AuthError, match="read-only and cannot be replaced"):
        launch.helper_json(
            [
                "query",
                "--file",
                str(books / "a.bean"),
                "--format",
                "text",
                "--output",
                str(keep),
                "--",
                "SELECT account",
            ]
        )

    assert keep.read_text() == "old"


def test_the_json_writer_refuses_a_read_only_export_on_its_own(books: Path) -> None:
    keep = books / "keep.txt"

    with pytest.raises(AuthError, match="read-only and cannot be replaced"):
        atomic_write(keep, "new", export=True)

    assert keep.read_text() == "old"


@MODES
def test_a_writable_destination_is_written(books: Path, as_json: bool) -> None:
    destination = books / "ok.out"
    destination.write_text("stale")
    destination.chmod(0o640)

    result = _query(books, destination, as_json=as_json)

    assert result.exit_code == 0, result.output
    written = destination.read_text()
    if as_json:
        assert json.loads(written)["data"]["rows"] == [["Assets:A"], ["Equity:B"]]
    else:
        assert "Assets:A" in written
    assert destination.stat().st_mode & 0o777 == 0o640
    assert not list(books.glob(".bea-*"))
