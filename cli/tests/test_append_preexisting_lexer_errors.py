"""An original dangling quote is reported at its written location before an append (w5/711)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HEADER = "2026-01-01 open Assets:Cash USD\n2026-01-01 open Expenses:Food USD\n"
BROKEN = '2026-01-02 note Assets:Cash "Called the bank about\n'
BOM = b"\xef\xbb\xbf"


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
        NO_COLOR="1",
        TERM="dumb",
    )
    return env


def _bea(root: Path, *args: str, as_json: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "cli.main",
            *(["--json"] if as_json else []),
            "--no-input",
            "--file",
            str(root),
            *args,
        ],
        cwd=root.parent,
        env=_env(root.parent),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _books(
    directory: Path, *, included: bool, bom: bool = False, ending: str = "\n", final_newline: bool = True
) -> tuple[Path, Path, int]:
    root = directory / "main.bean"
    target = directory / "broken.bean" if included else root
    if included:
        root.write_text(HEADER + 'include "broken.bean"\n')
    text = ("" if included else HEADER) + BROKEN
    if not final_newline:
        text = text.rstrip("\n")
    target.write_bytes((BOM if bom else b"") + text.replace("\n", ending).encode())
    return root, target, 1 if included else 3


def _args(root: Path, operation: str) -> list[str]:
    if operation == "transaction":
        return [
            "add",
            "transaction",
            "Lunch",
            "--date",
            "2026-01-05",
            "-p",
            "Expenses:Food 10 USD",
            "-p",
            "Assets:Cash",
        ]
    if operation == "note":
        return ["add", "note", "--date", "2026-01-05", "-a", "Assets:Cash", "-m", "done"]
    if operation == "bulk":
        rows = root.parent / "rows.json"
        rows.write_text(
            json.dumps(
                [
                    {
                        "date": "2026-01-05",
                        "narration": "Lunch",
                        "postings": [{"account": "Expenses:Food", "amount": "10 USD"}, {"account": "Assets:Cash"}],
                    }
                ]
            )
        )
        return ["add", "transactions", "--from", str(rows)]
    if operation == "open":
        return ["add", "open", "--date", "2026-01-05", "-a", "Assets:New", "--currency", "USD"]
    assert operation == "event"
    return ["add", "event", "--date", "2026-01-05", "--type", "review", "--description", "done"]


def _write(
    root: Path, target: Path, operation: str, *, allow_errors: bool, as_json: bool
) -> subprocess.CompletedProcess[str]:
    return _bea(
        root,
        *_args(root, operation),
        *(["--into", target.name] if target != root else []),
        *(["--allow-errors"] if allow_errors else []),
        as_json=as_json,
    )


def _assert_original_error(done: subprocess.CompletedProcess[str], target: Path, line: int, *, as_json: bool) -> None:
    assert done.returncode == 1, done.stdout + done.stderr
    assert done.stdout == ""
    if as_json:
        error = json.loads(done.stderr)["error"]
        assert error["category"] == "validation" and error["exit_code"] == 1
        message = str(error["message"])
        details = "\n".join(error["details"])
    else:
        message = details = " ".join(done.stderr.split())
    assert "The ledger already has" in message and "Fix the syntax error first" in message
    assert f"{target.name}:{line}:" in details
    assert "Invalid token" in details and "Called" in details
    assert "Proposed append" not in message + details
    assert "Lunch" not in message + details and "done" not in message + details
    assert "Pass --allow-errors" not in message + details


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
@pytest.mark.parametrize("allow_errors", [False, True], ids=["strict", "allow-errors"])
@pytest.mark.parametrize("included", [False, True], ids=["root", "included-target"])
@pytest.mark.parametrize("operation", ["transaction", "note"])
def test_a_dangling_original_quote_is_never_blamed_on_the_proposed_entry(
    tmp_path: Path, operation: str, included: bool, allow_errors: bool, as_json: bool
) -> None:
    root, target, line = _books(tmp_path, included=included)
    before = {path: path.read_bytes() for path in {root, target}}

    done = _write(root, target, operation, allow_errors=allow_errors, as_json=as_json)

    _assert_original_error(done, target, line, as_json=as_json)
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_bulk_add_names_the_existing_included_lexer_error_before_writing_rows(tmp_path: Path, as_json: bool) -> None:
    root, target, line = _books(tmp_path, included=True)
    before = {path: path.read_bytes() for path in {root, target}}

    done = _write(root, target, "bulk", allow_errors=True, as_json=as_json)

    _assert_original_error(done, target, line, as_json=as_json)
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize("operation", ["open", "event"])
def test_other_simple_directives_use_the_same_original_syntax_refusal(tmp_path: Path, operation: str) -> None:
    root, target, line = _books(tmp_path, included=False)
    before = root.read_bytes()

    done = _write(root, target, operation, allow_errors=True, as_json=True)

    _assert_original_error(done, target, line, as_json=True)
    assert root.read_bytes() == before


@pytest.mark.parametrize("allow_errors", [False, True], ids=["strict", "allow-errors"])
@pytest.mark.parametrize("included", [False, True], ids=["root", "included-target"])
def test_raw_engine_append_preserves_the_original_error_and_bytes(
    tmp_path: Path, included: bool, allow_errors: bool
) -> None:
    root, target, line = _books(tmp_path, included=included)
    before = {path: path.read_bytes() for path in {root, target}}
    done = subprocess.run(
        [
            sys.executable,
            "-m",
            "bea_engine",
            "append",
            "--file",
            str(root),
            "--text",
            '2026-01-05 note Assets:Cash "done"\n',
            *(["--into", target.name] if included else []),
            *(["--allow-errors"] if allow_errors else []),
        ],
        cwd=tmp_path,
        env=_env(tmp_path),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert done.returncode == 1, done.stdout + done.stderr
    error = json.loads(done.stdout)["error"]
    assert error["category"] == "validation"
    assert "Fix the syntax error first" in error["message"]
    assert any(f"{target}:{line}:" in detail and "Called" in detail for detail in error["details"])
    assert "Proposed append" not in done.stdout and "done" not in done.stdout
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize(
    ("bom", "ending", "final_newline"),
    [(True, "\n", True), (False, "\r\n", True), (False, "\n", False)],
    ids=["bom", "crlf", "eof-without-newline"],
)
def test_original_locations_survive_bom_crlf_and_unterminated_eof(
    tmp_path: Path, bom: bool, ending: str, final_newline: bool
) -> None:
    root, target, line = _books(tmp_path, included=False, bom=bom, ending=ending, final_newline=final_newline)
    before = root.read_bytes()

    done = _write(root, target, "transaction", allow_errors=True, as_json=True)

    _assert_original_error(done, target, line, as_json=True)
    assert root.read_bytes() == before


@pytest.mark.parametrize("as_json", [False, True], ids=["human-root", "json-included-target"])
def test_closing_the_original_quote_then_repeating_the_same_command_succeeds(tmp_path: Path, as_json: bool) -> None:
    root, target, line = _books(tmp_path, included=as_json)
    original = target.read_bytes()
    refused = _write(root, target, "transaction", allow_errors=False, as_json=as_json)
    _assert_original_error(refused, target, line, as_json=as_json)
    assert target.read_bytes() == original
    repaired = original.rstrip(b"\n") + b'"\n'
    target.write_bytes(repaired)

    added = _write(root, target, "transaction", allow_errors=False, as_json=as_json)

    assert added.returncode == 0, added.stdout + added.stderr
    assert target.read_bytes().startswith(repaired)
    assert target.read_text().count('2026-01-05 * "Lunch"') == 1
    checked = _bea(root, "check")
    assert checked.returncode == 0, checked.stdout + checked.stderr


@pytest.mark.parametrize(
    "note",
    [
        '2026-01-02 note Assets:Cash "Called the bank about\na fee"\n',
        r'2026-01-02 note Assets:Cash "Called the \"bank\" about it"' + "\n",
    ],
    ids=["valid-multiline-string", "escaped-quotes"],
)
def test_valid_multiline_or_escaped_strings_are_not_refused_as_unclosed(tmp_path: Path, note: str) -> None:
    root = tmp_path / "main.bean"
    root.write_text(HEADER + note)
    before = root.read_bytes()

    added = _write(root, root, "transaction", allow_errors=False, as_json=True)

    assert added.returncode == 0, added.stdout + added.stderr
    assert root.read_bytes().startswith(before)
    checked = _bea(root, "check")
    assert checked.returncode == 0, checked.stdout + checked.stderr


def test_semantic_preexisting_errors_keep_their_allow_errors_behavior(tmp_path: Path) -> None:
    root = tmp_path / "main.bean"
    root.write_text(HEADER + "2026-01-02 balance Assets:Cash 1 USD\n")
    before = root.read_bytes()
    strict = _write(root, root, "note", allow_errors=False, as_json=True)
    assert strict.returncode == 1, strict.stdout + strict.stderr
    assert "Pass --allow-errors" in json.loads(strict.stderr)["error"]["message"]
    assert root.read_bytes() == before

    allowed = _write(root, root, "note", allow_errors=True, as_json=True)

    assert allowed.returncode == 0, allowed.stdout + allowed.stderr
    assert root.read_bytes().startswith(before)
    assert any("Balance failed" in warning for warning in json.loads(allowed.stdout)["data"]["warnings"])
    assert root.read_text().count('2026-01-05 note Assets:Cash "done"') == 1


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_errors_from_a_new_entry_still_use_the_proposed_append_label(tmp_path: Path, as_json: bool) -> None:
    root = tmp_path / "main.bean"
    root.write_text(HEADER)
    before = root.read_bytes()

    refused = _bea(
        root,
        "add",
        "note",
        "--date",
        "2026-01-05",
        "-a",
        "Assets:Missing",
        "-m",
        "done",
        as_json=as_json,
    )

    assert refused.returncode == 1, refused.stdout + refused.stderr
    error = json.loads(refused.stderr)["error"] if as_json else None
    text = "\n".join(error["details"]) if error else " ".join(refused.stderr.split())
    assert "Proposed append (not written): Invalid reference to unknown account 'Assets:Missing'" in text
    assert "Fix the syntax error first" not in refused.stderr
    assert root.read_bytes() == before
