"""Plain `bea check` names a broken `plugin` line instead of printing a traceback (w5/256).

Text-mode check forwards to stock bean-check, which reports a plugin that
cannot load as an eleven-line Python traceback at `<load>:0`, naming neither
the ledger file nor the line. `--json check` and every other read already
gave `FILE:LINE: Cannot import plugin "NAME": CAUSE`; plain check now does too.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

MISSING = 'option "operating_currency" "USD"\nplugin "nonexistent_plugin_xyz"\n2026-01-01 open Assets:Cash USD\n'
UNBALANCED = '2026-01-02 * "lunch"\n  Assets:Cash  -5 USD\n  Expenses:Food  6 USD\n'
BOOM = '__plugins__ = ["boom"]\n\n\ndef boom(entries, options):\n    raise ValueError("Bad account mapping")\n'


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


def _ledger(tmp_path: Path, text: str) -> Path:
    ledger = tmp_path / "missing.bean"
    ledger.write_text(text, encoding="utf-8")
    return ledger


def _cannot_import(ledger: Path) -> str:
    return (
        f'{ledger}:2: Cannot import plugin "nonexistent_plugin_xyz": ModuleNotFoundError: '
        "No module named 'nonexistent_plugin_xyz'. Check the name is spelled right and the plugin is installed."
    )


def test_plain_check_names_the_plugin_line_in_two_lines(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, MISSING)

    result = _bea(tmp_path, "--file", "missing.bean", "check")

    assert result.returncode == 1, result.stderr
    assert result.stdout == ""
    assert result.stderr.splitlines() == [f"Error: {ledger}: 1 error(s).", f"  {_cannot_import(ledger)}"]


def test_plain_check_lists_the_other_load_errors_too(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, MISSING + "2026-01-01 open Expenses:Food USD\n" + UNBALANCED)

    result = _bea(tmp_path, "--file", str(ledger), "check")

    assert result.returncode == 1, result.stderr
    assert f"  {_cannot_import(ledger)}" in result.stderr.splitlines()
    assert f"{ledger}:5: Transaction does not balance" in result.stderr
    assert "Traceback" not in result.stderr
    assert "<load>" not in result.stderr


@pytest.mark.parametrize("flag", ["-v", "--auto"])
def test_bean_check_options_report_only_the_plugin_failure(tmp_path: Path, flag: str) -> None:
    # No open directives: `--auto` accepts these accounts, so a plain re-judgement must not list them.
    ledger = _ledger(tmp_path, MISSING.splitlines()[0] + '\nplugin "nonexistent_plugin_xyz"\n' + UNBALANCED)

    result = _bea(tmp_path, "--file", str(ledger), "check", flag)

    assert result.returncode == 1, result.stderr
    assert result.stderr.splitlines() == [
        f"Error: {ledger}: 1 plugin(s) failed to load.",
        f"  {_cannot_import(ledger)}",
    ]


def test_a_plugin_that_raises_while_running_is_named_too(tmp_path: Path) -> None:
    (tmp_path / "boom.py").write_text(BOOM, encoding="utf-8")
    ledger = _ledger(tmp_path, 'option "insert_pythonpath" "TRUE"\nplugin "boom"\n2026-01-01 open Assets:Cash USD\n')

    result = _bea(tmp_path, "--file", str(ledger), "check")

    assert result.returncode == 1, result.stderr
    assert result.stderr.splitlines() == [
        f"Error: {ledger}: 1 error(s).",
        f'  {ledger}:2: Plugin "boom" failed while running: ValueError: Bad account mapping.',
    ]


def test_debug_keeps_bean_checks_own_traceback(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, MISSING)

    result = _bea(tmp_path, "--debug", "--file", str(ledger), "check")

    assert result.returncode == 1, result.stderr
    assert "Traceback (most recent call last):" in result.stderr
    assert "ModuleNotFoundError: No module named 'nonexistent_plugin_xyz'" in result.stderr


def test_json_check_is_unchanged(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, MISSING)

    result = _bea(tmp_path, "--json", "--file", str(ledger), "check")

    assert result.returncode == 1, result.stderr
    assert json.loads(result.stderr)["error"] == {
        "category": "validation",
        "message": f"{ledger}: 1 error(s).",
        "exit_code": 1,
        "details": [_cannot_import(ledger)],
    }


def test_ledgers_without_a_failed_plugin_keep_bean_checks_output(tmp_path: Path) -> None:
    clean = _ledger(
        tmp_path, MISSING.replace('plugin "nonexistent_plugin_xyz"\n', 'plugin "beancount.plugins.noduplicates"\n')
    )
    accepted = _bea(tmp_path, "--file", str(clean), "check")
    broken = tmp_path / "broken.bean"
    broken.write_text(
        "2026-01-01 open Assets:Cash USD\n2026-01-01 open Expenses:Food USD\n" + UNBALANCED, encoding="utf-8"
    )
    refused = _bea(tmp_path, "--file", str(broken), "check")

    assert (accepted.returncode, accepted.stdout, accepted.stderr) == (0, "", "")
    assert refused.returncode == 1
    # bean-check's own rendering: the location line, then the entry itself.
    assert refused.stderr.startswith(f"{broken}:3: Transaction does not balance")
    assert "Error:" not in refused.stderr
