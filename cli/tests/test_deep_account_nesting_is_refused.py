"""An account too deep to report is refused by name, not with a traceback (w5/209).

A ledger `bea check` accepts could not be reported on once an account had a few
hundred components: encoding the tree overran Python's recursion limit after
the command body had returned, so the engine published no envelope and the
frontend printed "The Beancount engine did not answer" above a raw traceback.
Deeper still, building the tree failed as a bare `RecursionError`.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

import pytest

from bea_engine import protocol

ROOT = Path(__file__).resolve().parents[1]

# The encoder spends two frames per level, so 600 levels overrun the default
# limit of 1000 while encoding; 3000 overrun it earlier, building the tree.
ENCODING, BUILDING = 600, 3000
REPORTS = [
    ("balance",),
    ("report", "trial-balance"),
    ("report", "income-statement"),
    ("report", "balance-sheet"),
    ("report", "overview"),
]


def _bea(tmp_path: Path, levels: int, *args: str) -> subprocess.CompletedProcess[str]:
    account = "Expenses:" + ":".join(f"L{level}" for level in range(levels - 1))
    ledger = tmp_path / "main.bean"
    ledger.write_text(
        'option "operating_currency" "USD"\n'
        "2000-01-01 open Assets:Bank USD\n"
        f"2000-01-01 open {account} USD\n"
        '2001-02-03 * "t"\n'
        f"  {account}  1.00 USD\n"
        "  Assets:Bank\n",
        encoding="utf-8",
    )
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
        COLUMNS="200",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--file", str(ledger), *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def _refusal(levels: int) -> str:
    return f"Account nesting is too deep to report: 'Expenses:L0:L1:…:L{levels - 2}' is {levels} levels deep."


@pytest.mark.parametrize("command", REPORTS[:3], ids=" ".join)
def test_a_tree_too_deep_to_encode_is_refused_naming_the_depth(tmp_path: Path, command: tuple[str, ...]) -> None:
    done = _bea(tmp_path, ENCODING, *command)

    assert done.returncode == 1
    assert done.stdout == ""
    assert done.stderr.splitlines() == [f"Error: {_refusal(ENCODING)}"]


@pytest.mark.parametrize("command", REPORTS, ids=" ".join)
def test_a_tree_too_deep_to_build_is_refused_naming_the_depth(tmp_path: Path, command: tuple[str, ...]) -> None:
    done = _bea(tmp_path, BUILDING, *command)

    assert done.returncode == 1
    assert done.stdout == ""
    assert done.stderr.splitlines() == [f"Error: {_refusal(BUILDING)}"]


@pytest.mark.parametrize("levels", [ENCODING, BUILDING])
def test_the_refusal_is_a_validation_error_in_json(tmp_path: Path, levels: int) -> None:
    done = _bea(tmp_path, levels, "--json", "balance")

    assert done.returncode == 1
    assert done.stdout == ""
    error = json.loads(done.stderr)["error"]
    assert error["category"] == "validation"
    assert error["message"] == _refusal(levels)
    assert "Traceback" not in done.stderr


def test_debug_adds_no_engine_traceback_to_the_refusal(tmp_path: Path) -> None:
    done = _bea(tmp_path, ENCODING, "--debug", "balance")

    assert done.returncode == 1
    assert _refusal(ENCODING) in " ".join(done.stderr.split())
    assert "RecursionError" not in done.stderr
    assert "did not answer" not in done.stderr


@pytest.mark.parametrize("command", REPORTS, ids=" ".join)
def test_an_ordinarily_deep_account_still_reports(tmp_path: Path, command: tuple[str, ...]) -> None:
    done = _bea(tmp_path, 40, "--json", *command)

    assert done.returncode == 0, done.stderr
    assert done.stderr == ""
    if command[-1] in {"balance", "trial-balance", "income-statement"}:
        node, depth = json.loads(done.stdout)["data"]["expenses"], 1
        while node["children"]:
            node, depth = node["children"][0], depth + 1
        assert depth == 40
        assert node["balance"] == {"USD": "1.00"}


def test_other_commands_still_read_the_deep_ledger(tmp_path: Path) -> None:
    done = _bea(tmp_path, BUILDING, "check")

    assert done.returncode == 0, done.stderr


def _nested(levels: int) -> dict[str, Any]:
    root: dict[str, Any] = {}
    node = root
    for _ in range(levels):
        node["child"] = {}
        node = node["child"]
    return root


def test_an_answer_too_deep_to_encode_still_gets_an_envelope() -> None:
    stdout = io.StringIO()

    with redirect_stdout(stdout), pytest.raises(SystemExit) as exited, protocol.answering("probe") as answer:
        answer.data = _nested(5000)

    assert exited.value.code == protocol.EXIT_VALIDATION
    envelope = json.loads(stdout.getvalue())
    assert envelope["ok"] is False
    assert envelope["error"]["message"] == "The result nests too deeply to encode as an answer."
    assert "traceback" not in envelope["error"]


def test_a_command_names_what_was_nested_whether_computing_or_encoding_fails() -> None:
    def recurse() -> None:
        recurse()

    for fail_in_body in (True, False):
        stdout = io.StringIO()
        with redirect_stdout(stdout), pytest.raises(SystemExit) as exited, protocol.answering("probe") as answer:
            answer.too_deep = lambda: protocol.UsageError("named")
            if fail_in_body:
                recurse()
            answer.data = _nested(5000)

        assert exited.value.code == protocol.EXIT_USAGE
        error = json.loads(stdout.getvalue())["error"]
        assert (error["category"], error["message"]) == ("usage", "named")


def test_a_recursion_failure_without_a_named_refusal_keeps_its_traceback() -> None:
    def recurse() -> None:
        recurse()

    stdout = io.StringIO()
    with redirect_stdout(stdout), pytest.raises(SystemExit), protocol.answering("probe"):
        recurse()

    error = json.loads(stdout.getvalue())["error"]
    assert error["message"].startswith("RecursionError")
    assert "recurse" in error["traceback"]
