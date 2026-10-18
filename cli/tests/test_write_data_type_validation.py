"""Writes compare the same plugin data-type failures that check reports (w5/661)."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import Result
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
PLUGIN = """from beancount.core import data
from beancount.core.amount import Amount
from collections import UserDict
from decimal import Decimal
__plugins__ = ["corrupt"]
def corrupt(entries, options_map):
    mode = {mode!r}
    changed = any(isinstance(e, data.Note) for e in entries)
    result = []
    for entry in entries:
        if mode == "balance-switch" and changed and isinstance(entry, data.Balance):
            entry = entry._replace(amount=Amount(Decimal(0), "USD"), meta=UserDict(entry.meta))
        if isinstance(entry, data.Transaction):
            if mode == "all" or (mode == "new" and entry.narration == "New"):
                entry = entry._replace(tags=None)
            elif mode == "switch" and entry.narration == "Old":
                entry = entry._replace(links=None) if changed else entry._replace(tags=None)
        result.append(entry)
    return result, []
"""
TRANSACTION = '2024-01-05 * "Old"\n  Expenses:Food 10 USD\n  Assets:Cash\n'


def _ledger(tmp_path: Path, mode: str, *, split: bool = False) -> Path:
    (tmp_path / "badtypes.py").write_text(PLUGIN.format(mode=mode))
    root = tmp_path / "main.bean"
    root.write_text(
        'option "insert_pythonpath" "TRUE"\nplugin "badtypes"\n'
        "2024-01-01 open Assets:Cash USD\n2024-01-01 open Expenses:Food USD\n"
        + ('include "entries.bean"\n' if split else TRANSACTION)
    )
    if split:
        (tmp_path / "entries.bean").write_text(TRANSACTION)
    return root


def _invoke(root: Path, json_output: bool, *args: str) -> Result:
    return runner.invoke(app, [*(["--json"] if json_output else []), "--file", str(root), *args])


def _error(result: Result, json_output: bool) -> str:
    return json.dumps(json.loads(result.stderr)["error"]) if json_output else " ".join(result.output.split())


NEW = ["add", "transaction", "New", "--date", "2024-01-06", "-p", "Expenses:Food 5 USD", "-p", "Assets:Cash"]
NOTE = ["add", "note", "--date", "2024-01-06", "-a", "Assets:Cash", "--message", "Review"]


@pytest.mark.parametrize("allow_errors", [False, True])
@pytest.mark.parametrize("split", [False, True])
@pytest.mark.parametrize("json_output", [False, True])
def test_a_new_malformed_transaction_is_always_refused(
    tmp_path: Path, allow_errors: bool, split: bool, json_output: bool
) -> None:
    root = _ledger(tmp_path, "all", split=split)
    before = {path: path.read_bytes() for path in tmp_path.glob("*.bean")}
    initial = _invoke(root, True, "check")
    assert initial.exit_code == 1, initial.output

    result = _invoke(root, json_output, *NEW, *(["--allow-errors"] if allow_errors else []))

    assert result.exit_code == 1, result.output
    diagnostic = _error(result, json_output)
    assert "Invalid data types: Invalid tags type" in diagnostic
    if allow_errors:
        assert "introduce 1 new ledger error" in diagnostic
        assert "Proposed append (not written)" in diagnostic
    else:
        assert "ledger already has 1 error" in diagnostic
        assert "Pass --allow-errors" in diagnostic
        assert "new errors are still refused" in diagnostic
    assert ".bea-" not in diagnostic
    assert {path: path.read_bytes() for path in tmp_path.glob("*.bean")} == before
    final = _invoke(root, True, "check")
    assert final.exit_code == 1
    assert json.loads(final.stderr)["error"]["details"] == json.loads(initial.stderr)["error"]["details"]


@pytest.mark.parametrize("json_output", [False, True])
def test_allow_errors_only_permits_a_write_that_keeps_the_old_failure(tmp_path: Path, json_output: bool) -> None:
    root = _ledger(tmp_path, "all")
    before = root.read_bytes()

    refused = _invoke(root, json_output, *NOTE)
    assert refused.exit_code == 1, refused.output
    assert "ledger already has 1 error" in _error(refused, json_output)
    assert root.read_bytes() == before

    allowed = _invoke(root, json_output, *NOTE, "--allow-errors")
    assert allowed.exit_code == 0, allowed.output
    assert "Invalid data types: Invalid tags type" in allowed.output
    assert root.read_text().count(" note Assets:Cash ") == 1
    check = _invoke(root, True, "check")
    assert check.exit_code == 1
    assert len(json.loads(check.stderr)["error"]["details"]) == 1


@pytest.mark.parametrize("allow_errors", [False, True])
@pytest.mark.parametrize("json_output", [False, True])
def test_a_clean_baseline_never_hides_a_new_data_type_error(
    tmp_path: Path, allow_errors: bool, json_output: bool
) -> None:
    root = _ledger(tmp_path, "new")
    before = root.read_bytes()
    assert _invoke(root, True, "check").exit_code == 0

    result = _invoke(root, json_output, *NEW, *(["--allow-errors"] if allow_errors else []))

    assert result.exit_code == 1, result.output
    text = _error(result, json_output)
    assert "Invalid data types" in text
    assert "ledger already has" not in text
    assert root.read_bytes() == before


@pytest.mark.parametrize("split", [False, True])
@pytest.mark.parametrize("json_output", [False, True])
def test_a_different_violation_on_the_same_old_entry_is_new(tmp_path: Path, split: bool, json_output: bool) -> None:
    root = _ledger(tmp_path, "switch", split=split)
    before = {path: path.read_bytes() for path in tmp_path.glob("*.bean")}

    result = _invoke(root, json_output, *NOTE, "--allow-errors")

    assert result.exit_code == 1, result.output
    diagnostic = _error(result, json_output)
    assert "introduce 1 new ledger error" in diagnostic
    assert "Invalid data types: Invalid links type" in diagnostic
    assert str(tmp_path / "entries.bean" if split else root) in diagnostic
    assert ".bea-" not in diagnostic
    assert {path: path.read_bytes() for path in tmp_path.glob("*.bean")} == before


@pytest.mark.parametrize("json_output", [False, True])
def test_a_balance_failure_never_matches_a_new_data_type_failure(tmp_path: Path, json_output: bool) -> None:
    root = _ledger(tmp_path, "balance-switch")
    original = root.read_text().replace(TRANSACTION, "") + "2024-01-05 balance Assets:Cash 7 USD\n"
    root.write_text(original)

    result = _invoke(root, json_output, *NOTE, "--allow-errors")

    assert result.exit_code == 1, result.output
    text = _error(result, json_output)
    assert "introduce 1 new ledger error" in text
    assert "Invalid data types: Invalid type for meta" in text
    assert root.read_text() == original


def test_cached_load_validation_never_accumulates_errors(tmp_path: Path) -> None:

    root = _ledger(tmp_path, "all")
    # Isolate Beancount's global loader configuration from other tests.
    cache = tmp_path / "loaded.picklecache"
    script = """from pathlib import Path
import sys
from beancount import loader
from bea_engine import managed_load
loader.PICKLE_CACHE_THRESHOLD = 0
loader.initialize(True, sys.argv[2])
loaded = [managed_load.load_file(Path(sys.argv[1]), check_types=True) for _ in range(3)]
assert all(len(errors) == 1 for _, errors, _ in loaded)
assert all("Invalid tags type" in errors[0].message for _, errors, _ in loaded)
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(root), str(cache)],
        capture_output=True,
        text=True,
        timeout=30,
        env={
            **os.environ,
            "BEANCOUNT_LOAD_CACHE_FILENAME": str(cache),
            "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
        },
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert cache.is_file()
