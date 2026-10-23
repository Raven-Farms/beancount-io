"""A trailing carriage return reaches the formatter's fixed point in one pass (w5/712)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BOM = b"\xef\xbb\xbf"
HEADER = b"2026-01-01 open Assets:Cash USD\n2026-01-01 open Expenses:Food USD\n"
BODY = HEADER + b'2026-01-02 note Assets:Cash "kept\rstring"\n; interior\rcomment\n; c'
CANONICAL = BODY + b"\n"
CASES = [
    pytest.param(BODY + b"\r", id="one-eof-cr"),
    pytest.param(BODY + b"\r\r", id="two-eof-crs"),
    pytest.param(BODY + b"\r\r\r", id="three-eof-crs"),
    pytest.param(BODY, id="missing-final-lf-control"),
    pytest.param(CANONICAL.replace(b"\n", b"\r\n"), id="crlf-control"),
    pytest.param(BODY + b"\r\r\r\r\n", id="repeated-cr-before-lf"),
    pytest.param(BOM + BODY + b"\r", id="bom-and-eof-cr"),
]


def _env(directory: Path) -> dict[str, str]:
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
    return env


def _bea(
    directory: Path, *args: str, as_json: bool = True, stdin: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *(["--json"] if as_json else []), "--no-input", *args],
        cwd=directory,
        env=_env(directory),
        input=stdin,
        stdin=None if stdin is not None else subprocess.DEVNULL,
        capture_output=True,
        timeout=60,
    )


def _success(done: subprocess.CompletedProcess[bytes]) -> None:
    assert done.returncode == 0, (done.stdout + done.stderr).decode(errors="replace")


def _converges(directory: Path, root: Path, *, as_json: bool) -> bytes:
    _success(_bea(directory, "format", "-i", str(root), as_json=as_json))
    first = root.read_bytes()
    _success(_bea(directory, "format", "--check", str(root), as_json=as_json))
    second = _bea(directory, "format", "-i", str(root), as_json=as_json)
    _success(second)
    assert root.read_bytes() == first
    if as_json:
        assert json.loads(second.stdout)["data"]["formatted"] == []
    else:
        assert b"0/1 file(s) formatted" in second.stdout
    return first


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
@pytest.mark.parametrize("original", CASES)
def test_one_in_place_pass_removes_eof_crs_and_preserves_interior_content(
    tmp_path: Path, original: bytes, as_json: bool
) -> None:
    root = tmp_path / "main.bean"
    root.write_bytes(original)

    formatted = _converges(tmp_path, root, as_json=as_json)

    assert formatted == CANONICAL
    _success(_bea(tmp_path, "--file", str(root), "check"))
    notes = _bea(tmp_path, "--file", str(root), "list", "note")
    _success(notes)
    assert json.loads(notes.stdout)["data"][0]["comment"] == "kept\rstring"


@pytest.mark.parametrize("count", [1, 2], ids=["one-eof-cr", "two-eof-crs"])
@pytest.mark.parametrize("source", ["file", "stdin"])
@pytest.mark.parametrize("destination", ["stdout", "json-output"])
def test_named_and_stdin_rendering_have_the_same_fixed_point_bytes(
    tmp_path: Path, count: int, source: str, destination: str
) -> None:
    original = BODY + b"\r" * count
    root = tmp_path / "main.bean"
    root.write_bytes(original)
    exported = tmp_path / "formatted.out"
    args = ["format", str(root) if source == "file" else "-"]
    if destination == "json-output":
        args += ["--output", str(exported)]

    done = _bea(
        tmp_path,
        *args,
        as_json=destination == "json-output",
        stdin=original if source == "stdin" else None,
    )

    _success(done)
    actual = done.stdout if destination == "stdout" else exported.read_bytes()
    assert actual == CANONICAL
    assert root.read_bytes() == original
    # Feeding the actual rendered bytes back through stdin must already be stable.
    repeated = _bea(tmp_path, "format", "-", as_json=False, stdin=actual)
    _success(repeated)
    assert repeated.stdout == actual


def _write_args(directory: Path, operation: str) -> list[str]:
    if operation == "transaction":
        return [
            "add",
            "transaction",
            "New entry",
            "--date",
            "2026-01-05",
            "-p",
            "Expenses:Food 3 USD",
            "-p",
            "Assets:Cash",
        ]
    if operation == "note":
        return ["add", "note", "--date", "2026-01-05", "-a", "Assets:Cash", "-m", "New entry"]
    assert operation == "bulk"
    source = directory / "rows.json"
    source.write_text(
        json.dumps(
            [
                {
                    "date": "2026-01-05",
                    "narration": "New entry",
                    "postings": [{"account": "Expenses:Food", "amount": "3 USD"}, {"account": "Assets:Cash"}],
                }
            ]
        )
    )
    return ["add", "transactions", "--from", str(source)]


@pytest.mark.parametrize("ending", [b"\n", b"\r\n"], ids=["lf-dominance", "crlf-dominance"])
@pytest.mark.parametrize("operation", ["transaction", "note", "bulk", "raw"])
def test_append_preserves_the_tail_and_inserts_a_real_blank_line_before_the_new_entry(
    tmp_path: Path, operation: str, ending: bytes
) -> None:
    root = tmp_path / "main.bean"
    count = 2 if operation in {"bulk", "raw"} else 1
    original = HEADER.replace(b"\n", ending) + b"; c" + b"\r" * count
    if ending == b"\r\n":
        original = BOM + original
    root.write_bytes(original)
    if operation == "raw":
        added = subprocess.run(
            [
                sys.executable,
                "-m",
                "bea_engine",
                "append",
                "--file",
                str(root),
                "--text",
                '2026-01-05 note Assets:Cash "New entry"\n',
            ],
            cwd=tmp_path,
            env=_env(tmp_path),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=60,
        )
    else:
        added = _bea(tmp_path, "--file", str(root), *_write_args(tmp_path, operation), as_json=operation != "note")

    _success(added)
    written = root.read_bytes()
    assert written.startswith(original)
    assert written[len(original) :].startswith(ending + ending + b"2026-01-05 ")
    _success(_bea(tmp_path, "--file", str(root), "check"))
    kind = "note" if operation in {"note", "raw"} else "transaction"
    listed = _bea(tmp_path, "--file", str(root), "list", kind)
    _success(listed)
    rows = json.loads(listed.stdout)["data"]
    assert len(rows) == 1 and rows[0]["comment" if kind == "note" else "narration"] == "New entry"

    _converges(tmp_path, root, as_json=True)

    _success(_bea(tmp_path, "--file", str(root), "check"))
    after = _bea(tmp_path, "--file", str(root), "list", kind)
    _success(after)
    assert json.loads(after.stdout)["data"] == rows
