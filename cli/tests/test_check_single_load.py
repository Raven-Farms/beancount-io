"""`bea check` loads a clean ledger once, plugins included (w5/430).

It ran the helper's load and then native `bean-check`, so a plugin's warnings
printed twice and a plugin with side effects ran twice, where stock
`bean-check` runs it once. A ledger with errors, or a run with bean-check
options, still gets bean-check's own output.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = """\
import logging
import warnings
from pathlib import Path

__plugins__ = ["run"]


def run(entries, options_map):
    warnings.warn("wplug user warning")
    logging.warning("wplug logged a warning")
    with (Path(__file__).parent / "runs.txt").open("a") as runs:
        runs.write("run\\n")
    return entries, []
"""
LEDGER = 'plugin "wplug"\noption "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n'


def _check(tmp_path: Path, ledger: str, *args: str) -> tuple[subprocess.CompletedProcess[str], int]:
    plugins = tmp_path / "pl"
    plugins.mkdir(exist_ok=True)
    (plugins / "wplug.py").write_text(PLUGIN)
    (plugins / "runs.txt").unlink(missing_ok=True)
    (tmp_path / "main.bean").write_text(ledger)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=os.pathsep.join([str(ROOT / "src"), str(plugins)]),
        TERM="dumb",
        NO_COLOR="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), "check", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )
    return result, (plugins / "runs.txt").read_text().count("run")


def test_a_clean_ledger_runs_each_plugin_once(tmp_path: Path) -> None:
    result, runs = _check(tmp_path, LEDGER)
    assert result.returncode == 0, result.stderr
    assert runs == 1
    assert result.stderr.count("wplug user warning") == 2  # the warning line and its source line
    assert result.stderr.count("WARNING:root:wplug logged a warning") == 1


@pytest.mark.parametrize(
    ("ledger", "args", "code"),
    [
        (LEDGER + "2026-01-02 balance Assets:Cash 5 USD\n", [], 1),
        (LEDGER, ["--no-cache"], 0),
    ],
    ids=["errors", "bean-check-option"],
)
def test_errors_and_options_still_go_through_bean_check(
    tmp_path: Path, ledger: str, args: list[str], code: int
) -> None:
    result, runs = _check(tmp_path, ledger, *args)
    assert result.returncode == code, result.stderr
    assert runs == 2
    if code:
        # bean-check's own rendering: the message, then the entry it is about.
        assert "main.bean:4: Balance failed for 'Assets:Cash'" in result.stderr
        assert "   2026-01-02 balance Assets:Cash" in result.stderr
