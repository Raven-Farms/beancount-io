"""`bea check --auto` leaves no auto-plugin load in the shared load cache (w5/111).

Beancount keys its pickle cache on the files a load read, not on the plugin
set. On a ledger slow enough to be cached, `check --auto` stored a load made
with the auto-insert plugins, and plain `check`, `--json check`, `balance`
and `list` then called a ledger valid that references an unopened account.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.commands.check import _enables_auto
from cli.engine import launch
from cli.main import app

runner = CliRunner()

# Beancount caches a load only when it took a second; this plugin makes a
# three-line ledger that slow without sixty thousand transactions.
SLOW_PLUGIN = """\
import time

__plugins__ = ["slow"]


def slow(entries, options_map):
    time.sleep(1.05)
    return entries, []
"""
HEADER = 'option "insert_pythonpath" "TRUE"\nplugin "w5_111_slow"\n2000-01-01 open Assets:Bank USD\n'
SPEND = '2021-01-01 * "tail"\n  Expenses:Food  1234.00 USD\n  Assets:Bank\n'
UNOPENED = HEADER + SPEND
VALID = HEADER + "2000-01-01 open Expenses:Food\n" + SPEND


def _ledger(tmp_path: Path, text: str) -> Path:
    (tmp_path / "w5_111_slow.py").write_text(SLOW_PLUGIN)
    ledger = tmp_path / "main.bean"
    ledger.write_text(text)
    return ledger


def _bea(ledger: Path, *args: str, as_json: bool = False) -> Any:
    return runner.invoke(app, [*(["--json"] if as_json else []), "--file", str(ledger), *args])


def _cache(ledger: Path) -> Path:
    return Path(launch.load_cache_pattern(ledger).format(filename=ledger.name))


@pytest.mark.parametrize(
    ("args", "auto"),
    [
        (["--auto"], True),
        (["-a"], True),
        (["-va"], True),
        (["-v", "--no-cache"], False),
        (["--cache-filename", "-a"], False),
        (["--", "-a"], False),
    ],
)
def test_auto_is_recognized_as_bean_check_reads_it(args: list[str], auto: bool) -> None:
    assert _enables_auto(args) is auto


def test_later_commands_still_report_the_unopened_account(tmp_path: Path, bea_config_dir: Path) -> None:
    ledger = _ledger(tmp_path, UNOPENED)

    assert _bea(ledger, "check", "--auto").exit_code == 0

    plain = _bea(ledger, "check")
    assert plain.exit_code == 1, plain.output
    assert "unknown account 'Expenses:Food'" in plain.output
    checked = _bea(ledger, "check", as_json=True)
    assert checked.exit_code == 1, checked.output
    assert "unknown account 'Expenses:Food'" in checked.output
    balance = _bea(ledger, "balance", "Expenses", as_json=True)
    assert balance.exit_code == 1, balance.output
    assert "unknown account 'Expenses:Food'" in balance.output
    opened = _bea(ledger, "list", "open")
    assert opened.exit_code == 1, opened.output
    assert "generated" not in opened.output


def test_auto_is_not_answered_from_a_default_load(tmp_path: Path, bea_config_dir: Path) -> None:
    ledger = _ledger(tmp_path, UNOPENED)

    assert _bea(ledger, "check").exit_code == 1
    assert _cache(ledger).exists(), "the fixture must be slow enough to be cached"

    result = _bea(ledger, "check", "--auto")

    assert result.exit_code == 0, result.output


def test_ordinary_reads_of_a_valid_ledger_still_use_the_cache(tmp_path: Path, bea_config_dir: Path) -> None:
    ledger = _ledger(tmp_path, VALID)

    assert _bea(ledger, "check", "--auto").exit_code == 0
    assert _bea(ledger, "check").exit_code == 0
    assert _cache(ledger).exists()
    written = _cache(ledger).stat().st_mtime_ns

    checked = _bea(ledger, "check", as_json=True)

    assert checked.exit_code == 0, checked.output
    assert json.loads(checked.output)["data"] == {"valid": True, "errors": []}
    assert _cache(ledger).stat().st_mtime_ns == written
