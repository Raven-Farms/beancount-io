"""Engine path permissions produce useful failures before writes run (w5/673)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAPPING = "date=Date,narration=Description,amount=Amount"
pytestmark = pytest.mark.skipif(
    os.name != "posix" or os.geteuid() == 0, reason="requires POSIX permissions binding the current user"
)


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(
        'option "operating_currency" "USD"\n'
        'include "inc.bean"\n'
        "2026-01-01 open Assets:Checking USD\n"
        "2026-01-01 open Expenses:Food USD\n"
        "2026-01-01 open Expenses:Uncategorized USD\n"
    )
    (tmp_path / "inc.bean").write_text("; transactions go here\n")
    (tmp_path / "s.csv").write_text("Date,Description,Amount\n2026-02-03,Cafe,-5.00\n")
    (tmp_path / "rules.toml").write_text('[[rule]]\nmatch = "cafe"\naccount = "Expenses:Food"\n')
    (tmp_path / "rows.json").write_text(
        json.dumps(
            [
                {
                    "date": "2026-02-03",
                    "narration": "Bulk coffee",
                    "postings": [
                        {"account": "Assets:Checking", "units": {"number": "-5", "currency": "USD"}},
                        {"account": "Expenses:Food", "units": {"number": "5", "currency": "USD"}},
                    ],
                }
            ]
        )
    )
    return tmp_path


def _run(books: Path, *args: str, structured: bool) -> subprocess.CompletedProcess[str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_") and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        BEA_ENGINE_DIR=str(books / "engine"),
        BEA_NO_UPDATE_NOTIFIER="1",
        XDG_CACHE_HOME=str(books / "cache"),
        XDG_DATA_HOME=str(books / "data"),
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "cli.main",
            "--no-input",
            *(["--json"] if structured else []),
            "--file",
            str(books / "main.bean"),
            *args,
        ],
        cwd=books,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _originals(books: Path) -> dict[str, bytes]:
    return {name: (books / name).read_bytes() for name in ("main.bean", "inc.bean", "s.csv", "rules.toml", "rows.json")}


def _message(result: subprocess.CompletedProcess[str], structured: bool, code: int) -> str:
    assert result.returncode == code, result.stdout + result.stderr
    assert result.stdout == "", result.stdout
    if structured:
        error = json.loads(result.stderr)["error"]
        assert error["category"] == ("auth" if code == 3 else "usage"), error
        assert error["exit_code"] == code
        message = str(error["message"])
    else:
        assert any(line.startswith("Error: ") for line in result.stderr.splitlines()), result.stderr
        message = result.stderr
    for misleading in ("engine did not answer", "outcome is unknown", "Traceback", "Invalid value for", "Usage:"):
        assert misleading not in result.stderr
    return message


def _import_args(*, apply: bool, into: bool = False) -> list[str]:
    return [
        "import",
        "s.csv",
        "--csv",
        MAPPING,
        "--account",
        "Assets:Checking",
        "--rules",
        "rules.toml",
        *(["--into", "inc.bean"] if into else []),
        *(["--apply"] if apply else []),
    ]


def _into_args(operation: str) -> list[str]:
    if operation == "open":
        return ["add", "open", "--date", "2026-02-03", "--account", "Assets:New", "--into", "inc.bean"]
    if operation == "bulk":
        return ["add", "transactions", "--from", "rows.json", "--into", "inc.bean"]
    return _import_args(apply=operation == "import-apply", into=True)


@pytest.mark.parametrize("operation", ["open", "bulk", "import-preview", "import-apply"])
@pytest.mark.parametrize("structured", [False, True], ids=["text", "json"])
def test_unreadable_into_include_is_a_usage_failure_without_writes(
    books: Path, operation: str, structured: bool
) -> None:
    before = _originals(books)
    include = books / "inc.bean"
    include.chmod(0o000)
    try:
        assert not os.access(include, os.R_OK), "mode-000 fixture must actually be unreadable"
        result = _run(books, *_into_args(operation), structured=structured)
    finally:
        include.chmod(0o644)

    message = _message(result, structured, 2)
    assert (
        f"Included file '{include}' (included from '{books / 'main.bean'}') is not readable: Permission denied."
        in message
    )
    assert _originals(books) == before


@pytest.mark.parametrize("apply", [False, True], ids=["preview", "apply"])
@pytest.mark.parametrize("structured", [False, True], ids=["text", "json"])
def test_unreadable_rules_are_a_usage_failure_without_writes(books: Path, apply: bool, structured: bool) -> None:
    before = _originals(books)
    rules = books / "rules.toml"
    rules.chmod(0o000)
    try:
        assert not os.access(rules, os.R_OK), "mode-000 fixture must actually be unreadable"
        result = _run(books, *_import_args(apply=apply), structured=structured)
    finally:
        rules.chmod(0o644)

    message = _message(result, structured, 2)
    assert "Cannot read rules file" in message
    assert "rules.toml" in message
    assert "Permission denied" in message
    assert _originals(books) == before


@pytest.mark.parametrize("mode", [0o300, 0o555], ids=["write-search-no-read", "read-search-no-write"])
@pytest.mark.parametrize("structured", [False, True], ids=["text", "json"])
def test_export_directory_permissions_are_auth_failures_without_writes(
    books: Path, mode: int, structured: bool
) -> None:
    before = _originals(books)
    output = books / "export"
    output.mkdir()
    (output / "keep.txt").write_bytes(b"existing export marker\n")
    existing = {path.name: path.read_bytes() for path in output.iterdir()}
    output.chmod(mode)
    try:
        assert not os.access(output, os.R_OK if mode == 0o300 else os.W_OK)
        result = _run(books, "price", "export", "-o", "export", structured=structured)
    finally:
        output.chmod(0o755)

    message = _message(result, structured, 3)
    assert "export" in message.lower()
    assert ("not readable/searchable" if mode == 0o300 else "not writable") in message
    assert {path.name: path.read_bytes() for path in output.iterdir()} == existing
    assert _originals(books) == before


@pytest.mark.parametrize("operation", ["open", "bulk", "import-preview", "import-apply"])
def test_a_readable_include_accepts_the_same_operations(books: Path, operation: str) -> None:
    root_before = (books / "main.bean").read_bytes()
    include_before = (books / "inc.bean").read_bytes()

    result = _run(books, *_into_args(operation), structured=True)

    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(result.stdout)["data"]
    assert data["written"] == (0 if operation == "import-preview" else 1)
    assert (books / "main.bean").read_bytes() == root_before
    include_after = (books / "inc.bean").read_bytes()
    if operation == "import-preview":
        assert include_after == include_before
    else:
        assert include_after != include_before


def test_readable_rules_still_categorize_a_successful_apply(books: Path) -> None:
    result = _run(books, *_import_args(apply=True), structured=True)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Expenses:Food" in json.loads(result.stdout)["data"]["rows"][0]["entry"]
    assert '"Cafe"' in (books / "main.bean").read_text()


def test_a_readable_writable_export_directory_still_works(books: Path) -> None:
    before = _originals(books)
    output = books / "export"
    output.mkdir()
    (output / "keep.txt").write_bytes(b"existing export marker\n")

    result = _run(books, "price", "export", "-o", "export", structured=True)

    assert result.returncode == 0, result.stdout + result.stderr
    assert len(json.loads(result.stdout)["data"]["files"]) == 2
    assert (output / "main.bean").read_bytes() == before["main.bean"]
    assert (output / "inc.bean").read_bytes() == before["inc.bean"]
    assert (output / "keep.txt").read_bytes() == b"existing export marker\n"
    assert _originals(books) == before
