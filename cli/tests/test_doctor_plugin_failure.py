"""Doctor refuses a ledger whose plugin cannot be imported or crashes (w5/439).

Upstream logs the traceback and carries on without the plugin: `roundtrip`
printed it, then "Entries are the same. Congratulations." with exit 0, and
`missing-open` answered for entries the plugin never ran on. `bea check`
rejects the same ledger in one line.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REST = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n'


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize(
    ("plugin", "failure"),
    [
        ("no.such.plugin", 'main.bean:1: Cannot import plugin "no.such.plugin": ModuleNotFoundError'),
        ("beancount.plugins.currency_accounts", 'main.bean:1: Plugin "beancount.plugins.currency_accounts" failed'),
    ],
    ids=["import", "run"],
)
@pytest.mark.parametrize("op", ["roundtrip", "missing-open", "print-options", "display-context"])
def test_a_plugin_failure_is_refused_in_checks_form(tmp_path: Path, plugin: str, failure: str, op: str) -> None:
    main = tmp_path / "main.bean"
    main.write_text(f'plugin "{plugin}"\n{REST}')

    result = _bea(tmp_path, "doctor", op, str(main))

    assert result.returncode == 1, result.stdout + result.stderr
    assert f"Error: doctor {op} cannot load {main}: {tmp_path / failure}" in result.stderr
    assert "Traceback" not in result.stderr
    assert "Congratulations" not in result.stdout + result.stderr


def test_a_working_plugin_still_round_trips(tmp_path: Path) -> None:
    main = tmp_path / "main.bean"
    main.write_text('plugin "beancount.plugins.auto_accounts"\n' + REST)
    result = _bea(tmp_path, "doctor", "roundtrip", str(main))
    assert result.returncode == 0, result.stderr
    assert "Congratulations" in result.stderr
