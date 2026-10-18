"""A plugin refusal identifies the proposed change even when anchored in old text (w5/666)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASE = """2026-01-01 open Assets:Cash
2026-01-01 open Expenses:Food
2026-01-10 * "Lunch"
  Expenses:Food 5 USD
  Assets:Cash -5 USD
"""
CASES = {
    "leafonly": (
        BASE,
        ("open", "--date", "2026-01-07", "--account", "Expenses:Food:Coffee"),
        "Non-leaf account",
    ),
    "coherent_cost": (
        BASE.replace("5 USD", "1 HOOL"),
        (
            "transaction",
            "buy",
            "--date",
            "2026-01-07",
            "-p",
            "Expenses:Food 1 HOOL {50 USD}",
            "-p",
            "Assets:Cash -50 USD",
        ),
        "used both with and without cost",
    ),
    "onecommodity": (
        BASE,
        ("transaction", "buy", "--date", "2026-01-07", "-p", "Expenses:Food 1 EUR", "-p", "Assets:Cash -1 EUR"),
        "More than one currency",
    ),
}


def _bea(tmp_path: Path, *args: str, json_mode: bool) -> tuple[int, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        PYTHONPATH=str(ROOT / "src"),
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        NO_COLOR="1",
        TERM="dumb",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cli.main",
            *(["--json"] if json_mode else []),
            "-f",
            str(tmp_path / "main.bean"),
            *args,
        ],
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )
    output = json.dumps(json.loads(result.stdout or result.stderr)) if json_mode else result.stdout + result.stderr
    return result.returncode, " ".join(output.split())


@pytest.mark.parametrize("plugin", CASES)
@pytest.mark.parametrize("json_mode", [False, True])
@pytest.mark.parametrize("allow_errors", [False, True])
def test_new_plugin_error_at_existing_line_names_its_trigger(
    tmp_path: Path,
    plugin: str,
    json_mode: bool,
    allow_errors: bool,
) -> None:
    body, args, error = CASES[plugin]
    ledger = tmp_path / "main.bean"
    ledger.write_text(f'plugin "beancount.plugins.{plugin}"\n' + body)
    before = ledger.read_bytes()
    code, output = _bea(tmp_path, "add", *args, *(["--allow-errors"] if allow_errors else []), json_mode=json_mode)
    assert code == 1, output
    assert error in output
    assert f"{ledger}:" in output
    assert f"proposed append (not written) triggers this error from plugin beancount.plugins.{plugin}" in output
    assert ledger.read_bytes() == before


@pytest.mark.parametrize("json_mode", [False, True])
def test_old_plugin_error_is_not_attributed_to_unrelated_append(tmp_path: Path, json_mode: bool) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text('plugin "beancount.plugins.leafonly"\n' + BASE + "2026-01-01 open Expenses:Food:Coffee\n")
    code, output = _bea(
        tmp_path,
        "add",
        "note",
        "--date",
        "2026-01-11",
        "-a",
        "Assets:Cash",
        "-m",
        "reviewed",
        "--allow-errors",
        json_mode=json_mode,
    )
    assert code == 0, output
    assert "Non-leaf account" in output
    assert "triggers this error" not in output
    assert '2026-01-11 note Assets:Cash "reviewed"' in ledger.read_text()


@pytest.mark.parametrize("json_mode", [False, True])
def test_late_proposed_open_names_date_remedy_without_unwritten_line(tmp_path: Path, json_mode: bool) -> None:
    ledger = tmp_path / "main.bean"
    body = (
        'plugin "beancount.plugins.auto_accounts"\n2026-01-02 * "Lunch"\n  Expenses:Food 5 USD\n  Assets:Cash -5 USD\n'
    )
    ledger.write_text(body)
    before = ledger.read_bytes()
    code, output = _bea(
        tmp_path, "add", "open", "--date", "2026-01-04", "-a", "Assets:Cash", "-c", "USD", json_mode=json_mode
    )
    assert code == 1, output
    assert "proposed open would open Assets:Cash on 2026-01-04; date it on or before 2026-01-02" in output
    assert f"{ledger}:9" not in output
    assert "date it on or before 2026-01-03" not in output
    assert "edit that directive" not in output
    assert ledger.read_bytes() == before
    code, output = _bea(
        tmp_path, "add", "open", "--date", "2026-01-02", "-a", "Assets:Cash", "-c", "USD", json_mode=json_mode
    )
    assert code == 0, output
    assert "2026-01-02 open Assets:Cash USD" in ledger.read_text()
