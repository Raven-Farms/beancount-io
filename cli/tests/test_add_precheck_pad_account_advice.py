"""Strict price/balance prechecks offer a remedy that can fix inactive pads (w5/682)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HEADER = (
    'option "operating_currency" "USD"\n'
    'include "preexisting.bean"\n'
    "2024-01-01 open Assets:Cash USD\n"
    "2024-01-01 open Equity:Opening USD\n"
)
COMMANDS = {
    "price": ["price", "--date", "2024-03-02", "--currency", "EUR", "--amount", "1.10 USD"],
    "balance": ["balance", "--date", "2024-03-02", "--account", "Assets:Cash", "--amount", "0 USD"],
}


def _bea(
    root: Path, operation: str, json_output: bool, *, allow_errors: bool = False
) -> subprocess.CompletedProcess[str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_") and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    env.update(
        BEA_CONFIG_DIR=str(root.parent / "config"),
        XDG_CACHE_HOME=str(root.parent / "cache"),
        XDG_DATA_HOME=str(root.parent / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
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
            *(["--json"] if json_output else []),
            "--file",
            str(root),
            "add",
            *COMMANDS[operation],
            *(["--allow-errors"] if allow_errors else []),
        ],
        env=env,
        cwd=root.parent,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _error(result: subprocess.CompletedProcess[str], json_output: bool) -> tuple[str, str]:
    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stdout == "", result.stdout
    assert "Traceback" not in result.stderr, result.stderr
    if json_output:
        error = json.loads(result.stderr)["error"]
        assert error["category"] == "validation" and error["exit_code"] == 1, error
        return error["message"], " ".join([error["message"], *error.get("details", [])])
    return " ".join(result.stderr.split()), " ".join(result.stderr.split())


def _books(tmp_path: Path, text: str) -> tuple[Path, Path]:
    root = tmp_path / "main.bean"
    root.write_text(HEADER)
    source = tmp_path / "preexisting.bean"
    source.write_text(text)
    return root, source


@pytest.mark.parametrize("operation", COMMANDS)
@pytest.mark.parametrize("json_output", [False, True], ids=["human", "json"])
@pytest.mark.parametrize("role", ["target", "source"])
@pytest.mark.parametrize("state", ["unopened", "before-open", "after-close"])
def test_invalid_pad_accounts_name_the_real_remedy_and_still_refuse_with_allow_errors(
    tmp_path: Path, operation: str, json_output: bool, role: str, state: str
) -> None:
    account = "Assets:Pad" if role == "target" else "Equity:Pad"
    target = account if role == "target" else "Assets:Cash"
    source_account = account if role == "source" else "Equity:Opening"
    declarations = {
        "unopened": "",
        "before-open": f"2024-02-10 open {account} USD\n",
        "after-close": f"2024-01-01 open {account} USD\n2024-01-20 close {account}\n",
    }[state]
    pad = f"2024-02-01 pad {target} {source_account}\n"
    root, source = _books(tmp_path, declarations + pad)
    line = len(declarations.splitlines()) + 1
    before = {path: path.read_bytes() for path in (root, source)}

    for allow_errors in (False, True):
        result = _bea(root, operation, json_output, allow_errors=allow_errors)
        message, diagnostic = _error(result, json_output)

        assert f"{source}:{line}:" in diagnostic and account in diagnostic, diagnostic
        assert "Invalid reference to " in diagnostic, diagnostic
        assert "nothing was written" in message.casefold(), message
        assert "Pass --allow-errors" not in diagnostic and "write anyway" not in diagnostic, diagnostic
        assert "--force" not in diagnostic, diagnostic
        if allow_errors:
            assert "Pad accounts must be active, even with --allow-errors." in diagnostic, diagnostic
        else:
            assert "2024-02-01" in diagnostic and target in diagnostic and source_account in diagnostic, diagnostic
            assert "pad" in message.casefold() and "open" in message.casefold(), message
            assert "correct the pad account/date" in message.casefold(), message
            assert "cannot bypass an inactive pad account" in message.casefold(), message
        assert {path: path.read_bytes() for path in (root, source)} == before
        assert not list(tmp_path.glob(".bea-*"))


@pytest.mark.parametrize("operation", COMMANDS)
@pytest.mark.parametrize("json_output", [False, True], ids=["human", "json"])
def test_an_existing_balance_error_keeps_the_flag_advice_and_the_flag_really_works(
    tmp_path: Path, operation: str, json_output: bool
) -> None:
    original_error = "2024-02-01 balance Assets:Cash 7 USD\n"
    root, source = _books(tmp_path, original_error)
    before = {path: path.read_bytes() for path in (root, source)}

    refused = _bea(root, operation, json_output)
    message, diagnostic = _error(refused, json_output)

    assert "Pass --allow-errors to write anyway." in message, message
    assert f"{source}:1: Balance failed for 'Assets:Cash'" in diagnostic, diagnostic
    assert "inactive pad" not in diagnostic
    assert {path: path.read_bytes() for path in (root, source)} == before

    allowed = _bea(root, operation, json_output, allow_errors=True)

    assert allowed.returncode == 0, allowed.stdout + allowed.stderr
    if json_output:
        assert json.loads(allowed.stdout)["data"]["written"] == 1
    assert root.read_bytes().startswith(before[root]) and root.read_bytes() != before[root]
    assert source.read_bytes() == before[source]
    directive = "2024-03-02 price EUR 1.10 USD" if operation == "price" else "2024-03-02 balance Assets:Cash 0 USD"
    assert directive in " ".join(root.read_text().split())


@pytest.mark.parametrize("operation", COMMANDS)
@pytest.mark.parametrize("json_output", [False, True], ids=["human", "json"])
def test_syntax_error_advice_keeps_priority_when_the_ledger_also_has_an_invalid_pad(
    tmp_path: Path, operation: str, json_output: bool
) -> None:
    text = '2024-02-01 pad Assets:Cash Equity:Missing\n2024-02-02 * "unterminated\n'
    root, source = _books(tmp_path, text)
    before = {path: path.read_bytes() for path in (root, source)}

    refused = _bea(root, operation, json_output)
    message, diagnostic = _error(refused, json_output)

    assert "including a syntax error" in message and "Fix the syntax error first" in message, message
    assert "Pass --allow-errors" not in message
    assert f"{source}:2:" in diagnostic and "Invalid reference to " in diagnostic, diagnostic
    assert {path: path.read_bytes() for path in (root, source)} == before
