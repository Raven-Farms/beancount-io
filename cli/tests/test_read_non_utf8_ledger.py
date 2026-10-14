"""A ledger that is not UTF-8 fails every read the way `format` does (w5/278).

`format` and `add` named the file, the byte offset and the remedy. `list`,
`balance`, `query` and `check` reported the parser's raw codec message as an
ordinary ledger error at a line, and suggested `--allow-errors`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Latin-1 `é` in the payee, at byte 42 of the file.
LATIN = b'2026-01-01 open Assets:A\n2026-01-02 * "caf\xe9"\n  Assets:A  1 USD\n  Assets:A  -1 USD\n'
ROOT_LEDGER = b'include "latin.bean"\n2026-01-01 open Assets:B\n'
# The same byte where the parser never decodes it.
COMMENT = b'2026-01-01 open Assets:A\n; caf\xe9\n2026-01-02 * "x"\n  Assets:A  1 USD\n  Assets:A  -1 USD\n'


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _refusal(path: Path) -> str:
    reason = "invalid continuation byte at byte 42"
    return f"Cannot decode '{path}' as UTF-8: {reason}. Re-save the file as UTF-8 and retry."


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "latin.bean").write_bytes(LATIN)
    (tmp_path / "main.bean").write_bytes(ROOT_LEDGER)
    (tmp_path / "comment.bean").write_bytes(COMMENT)
    return tmp_path


@pytest.mark.parametrize(
    "command",
    [
        ["list", "transaction"],
        ["balance"],
        ["balance", "--allow-errors"],
        ["query", "SELECT account"],
        ["check"],
        ["check", "-v"],
    ],
    ids=["list", "balance", "balance-allow-errors", "query", "check", "check-option"],
)
@pytest.mark.parametrize("ledger", ["latin.bean", "main.bean"], ids=["root", "include"])
def test_a_read_names_the_file_the_byte_and_the_remedy(books: Path, ledger: str, command: list[str]) -> None:
    result = _bea(books, "--file", ledger, *command)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.replace("\n", "") == f"Error: {_refusal(books / 'latin.bean')}"


@pytest.mark.parametrize(
    "command", [["list", "transaction"], ["query", "SELECT account"], ["check"]], ids=["list", "query", "check"]
)
def test_json_carries_the_same_refusal(books: Path, command: list[str]) -> None:
    result = _bea(books, "--file", "latin.bean", "--json", *command)

    assert result.returncode == 1
    assert result.stdout == ""
    assert json.loads(result.stderr) == {
        "error": {"category": "validation", "message": _refusal(books / "latin.bean"), "exit_code": 1}
    }


def test_format_is_unchanged(books: Path) -> None:
    result = _bea(books, "format", "latin.bean")

    assert result.returncode == 1
    assert result.stderr.replace("\n", "") == f"Error: {_refusal(books / 'latin.bean')}"
    assert (books / "latin.bean").read_bytes() == LATIN


@pytest.mark.parametrize("command", [["list", "transaction"], ["check"]], ids=["list", "check"])
def test_a_byte_the_parser_never_decodes_still_loads(books: Path, command: list[str]) -> None:
    result = _bea(books, "--file", "comment.bean", *command)

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
