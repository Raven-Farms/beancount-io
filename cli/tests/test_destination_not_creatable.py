"""A destination that cannot be created is refused by name, never as a raw OS error (w5/090).

`bea init DIR` and `bea format -o` printed a Python exception name and exited
1 — the validation category — when a path component was a regular file or the
directory was not writable. The first is a bad argument (2), the second the
filesystem refusing (3).
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
    (directory / "lock").mkdir(parents=True)
    (directory / "notes").write_text("n\n")
    (directory / "a.bean").write_text("2026-01-01 open Assets:A\n")
    (directory / "t.txt").write_text("Assets:A 1\n")
    (directory / "lock").chmod(0o555)
    monkeypatch.chdir(directory)
    yield directory
    (directory / "lock").chmod(0o755)


def _run(*args: str, as_json: bool = False) -> Any:
    return runner.invoke(app, [*(["--json"] if as_json else []), "--no-input", *args])


def _clean(result: Any) -> str:
    text = " ".join(result.output.split())
    for raw in ("Errno", "PermissionError", "FileExistsError", "NotADirectoryError", "Traceback", ".bea-"):
        assert raw not in text, text
    assert "Nothing was written" in text
    return text


def _tree(work: Path) -> list[str]:
    return sorted(str(path.relative_to(work)) for path in work.rglob("*"))


@pytest.mark.parametrize(
    ("args", "code", "named"),
    [
        (["init", "notes", "--currency", "USD"], 2, "notes"),
        (["init", "notes/deeper", "--currency", "USD"], 2, "notes"),
        (["init", "lock/books", "--currency", "USD"], 3, "lock"),
        (["format", "a.bean", "-o", "lock/out.txt"], 3, "lock/out.txt"),
        (["treeify", "t.txt", "-o", "lock/t.out"], 3, "lock/t.out"),
    ],
    ids=["init-over-a-file", "init-below-a-file", "init-in-read-only", "format-o-read-only", "treeify-o-read-only"],
)
def test_the_refusal_names_the_path_and_the_right_category(work: Path, args: list[str], code: int, named: str) -> None:
    before = _tree(work)

    result = _run(*args)

    assert result.exit_code == code, result.output
    assert named in _clean(result)
    assert _tree(work) == before


@pytest.mark.parametrize(
    ("args", "code", "category"),
    [
        (["init", "notes", "--currency", "USD"], 2, "usage"),
        (["init", "lock/books", "--currency", "USD"], 3, "auth"),
        (["format", "a.bean", "-o", "lock/out.txt"], 3, "auth"),
    ],
    ids=["init-over-a-file", "init-in-read-only", "format-o-read-only"],
)
def test_json_carries_the_same_category(work: Path, args: list[str], code: int, category: str) -> None:
    result = _run(*args, as_json=True)

    assert result.exit_code == code, result.output
    error = json.loads(result.stderr)["error"]
    assert (error["category"], error["exit_code"]) == (category, code)


def test_format_output_onto_a_read_only_file_is_refused(work: Path) -> None:
    target = work / "frozen.txt"
    target.write_text("keep\n")
    target.chmod(0o444)

    result = _run("format", "a.bean", "-o", "frozen.txt")

    assert result.exit_code == 3, result.output
    assert "frozen.txt" in _clean(result)
    assert target.read_text() == "keep\n"


def test_writable_destinations_still_work(work: Path) -> None:
    assert _run("format", "a.bean", "-o", "out.txt").exit_code == 0
    assert (work / "out.txt").read_text().startswith("2026-01-01 open Assets:A")
    assert _run("init", "fresh/books", "--currency", "USD").exit_code == 0
    assert _run("format", "a.bean", "-o", "nodir/out.txt").exit_code == 2
    assert _run("format", "a.bean", "-o", "/dev/null").exit_code == 0
