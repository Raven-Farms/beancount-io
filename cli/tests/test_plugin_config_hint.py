"""A plugin that needs a configuration string says so (w5/400).

`plugin "beancount.plugins.currency_accounts"` without its config failed
with a raw `TypeError … missing 1 required positional argument: 'config'`
and no hint about the `plugin "NAME" "CONFIG"` form.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HINT = 'This plugin needs a configuration string: plugin "beancount.plugins.currency_accounts" "CONFIG".'


def _check(books: Path, ledger: str, *flags: str) -> subprocess.CompletedProcess[str]:
    (books / "main.bean").write_text(ledger)
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
        [sys.executable, "-m", "cli.main", *flags, "-f", str(books / "main.bean"), "check"],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize("json_output", [False, True])
def test_a_plugin_missing_its_config_names_the_form(tmp_path: Path, json_output: bool) -> None:
    ledger = 'plugin "beancount.plugins.currency_accounts"\noption "operating_currency" "USD"\n'
    result = _check(tmp_path, ledger, *(["--json"] if json_output else []))
    assert result.returncode == 1
    text = "\n".join(json.loads(result.stderr)["error"]["details"]) if json_output else result.stderr
    assert 'Plugin "beancount.plugins.currency_accounts" failed while running: TypeError' in text
    assert HINT in text


def test_an_import_failure_has_no_config_hint(tmp_path: Path) -> None:
    result = _check(tmp_path, 'plugin "no.such.plugin"\noption "operating_currency" "USD"\n')
    assert result.returncode == 1
    assert 'Cannot import plugin "no.such.plugin"' in result.stderr
    assert "configuration string" not in result.stderr
