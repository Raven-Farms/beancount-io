"""Native check JSON reports early include failures at their actual sources (w5/672)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OPEN = "2024-01-01 open Assets:Cash USD\n"
LATIN = b'2024-01-02 note Assets:Cash "caf\xe9"\n'


def _check(directory: Path, root: Path, native_json: bool = True) -> subprocess.CompletedProcess[str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_") and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    env.update(
        BEA_CONFIG_DIR=str(directory / "config"),
        XDG_CACHE_HOME=str(directory / "cache"),
        XDG_DATA_HOME=str(directory / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--file", str(root), "check", *(["--json"] if native_json else [])],
        cwd=directory,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _one_error(result: subprocess.CompletedProcess[str], filename: Path, lineno: int) -> str:
    assert result.stderr == "", result.stderr
    answer = json.loads(result.stdout)
    assert set(answer) == {"errors"}, answer
    assert len(answer["errors"]) == 1, answer
    error = answer["errors"][0]
    assert error["filename"] == str(filename), error
    assert error["lineno"] == lineno, error
    assert isinstance(error["message"], str)
    return str(error["message"])


@pytest.mark.parametrize("link", ["symlink", "hardlink"])
@pytest.mark.parametrize("native_json", [True, False], ids=["native-json", "text-control"])
def test_duplicate_include_keeps_its_root_include_line(tmp_path: Path, link: str, native_json: bool) -> None:
    root = tmp_path / "main.bean"
    original = tmp_path / "a.bean"
    alias = tmp_path / "b.bean"
    root.write_text('include "a.bean"\ninclude "b.bean"\n' + OPEN)
    original.write_text("2024-01-01 open Expenses:Food USD\n")
    if link == "symlink":
        alias.symlink_to(original)
    else:
        os.link(original, alias)
    before = (root.read_bytes(), original.read_bytes())

    result = _check(tmp_path, root, native_json)

    assert result.returncode == 1, result.stdout + result.stderr
    if native_json:
        message = _one_error(result, root, 2)
        assert message.startswith("Duplicate include:"), message
    else:
        assert result.stdout == ""
        assert f"{root}:2: Duplicate include:" in result.stderr
        message = result.stderr
    assert f"{alias} is {original} under another name" in message
    assert "Traceback" not in message
    assert (root.read_bytes(), original.read_bytes()) == before
    assert alias.read_bytes() == original.read_bytes()


@pytest.mark.parametrize("kind", ["permission", "directory"])
@pytest.mark.parametrize("native_json", [True, False], ids=["native-json", "text-control"])
def test_unreadable_include_names_the_include_instead_of_the_root(tmp_path: Path, kind: str, native_json: bool) -> None:
    root = tmp_path / "main.bean"
    include = tmp_path / "blocked.bean"
    root.write_text(OPEN + 'include "blocked.bean"\n')
    if kind == "directory":
        include.mkdir()
        reason = "it is a directory, not a file"
        saved = None
    else:
        if os.geteuid() == 0:
            pytest.skip("root can read mode-000 files")
        include.write_text('2024-01-02 note Assets:Cash "read me"\n')
        saved = include.read_bytes()
        include.chmod(0o000)
        reason = "Permission denied"
    before = root.read_bytes()
    try:
        if kind == "permission" and os.access(include, os.R_OK):
            pytest.skip("this user reads mode-000 files")
        result = _check(tmp_path, root, native_json)
    finally:
        if kind == "permission":
            include.chmod(0o644)

    assert result.returncode == 2, result.stdout + result.stderr
    if native_json:
        message = _one_error(result, include, 0)
    else:
        assert result.stdout == ""
        assert len(result.stderr.strip().splitlines()) == 1, result.stderr
        message = result.stderr
    assert f"Included file '{include}' (included from '{root}') is not readable: {reason}." in message
    assert "Traceback" not in message
    assert root.read_bytes() == before
    if saved is not None:
        assert include.read_bytes() == saved
    else:
        assert include.is_dir()


@pytest.mark.parametrize("nested", [False, True], ids=["direct", "nested-colon-filename"])
@pytest.mark.parametrize("native_json", [True, False], ids=["native-json", "text-control"])
def test_undecodable_include_uses_the_bad_file_even_with_a_line_looking_colon(
    tmp_path: Path, nested: bool, native_json: bool
) -> None:
    root = tmp_path / "main.bean"
    if nested:
        directory = tmp_path / "parts:2026"
        directory.mkdir()
        bad = directory / "latin:7: notes.bean"
        middle = directory / "index.bean"
        middle.write_text('include "latin:7: notes.bean"\n')
        root.write_text(OPEN + 'include "parts:2026/index.bean"\n')
    else:
        bad = tmp_path / "latin.bean"
        root.write_text(OPEN + 'include "latin.bean"\n')
    bad.write_bytes(LATIN)
    before = {path: path.read_bytes() for path in tmp_path.rglob("*.bean")}

    result = _check(tmp_path, root, native_json)

    assert result.returncode == 1, result.stdout + result.stderr
    if native_json:
        message = _one_error(result, bad, 0)
    else:
        assert result.stdout == ""
        assert len(result.stderr.strip().splitlines()) == 1, result.stderr
        message = result.stderr
    assert f"Cannot decode '{bad}' as UTF-8:" in message
    assert "Re-save the file as UTF-8 and retry." in message
    assert "Traceback" not in message
    assert {path: path.read_bytes() for path in tmp_path.rglob("*.bean")} == before


def test_clean_native_json_remains_an_empty_error_list(tmp_path: Path) -> None:
    root = tmp_path / "main.bean"
    include = tmp_path / "child.bean"
    root.write_text(OPEN + 'include "child.bean"\n')
    include.write_text('2024-01-02 note Assets:Cash "hello"\n')

    result = _check(tmp_path, root)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert json.loads(result.stdout) == {"errors": []}
