"""`add close` keeps its funded-close guard where `check_drained` does not (w5/888).

Loading the plugin switched the CLI's check off entirely, but the plugin
skips a currency an explicit assertion already covers on the close date
(whatever it asserts) and never looks at Income or Expenses, so a close
over a balance went through, exit 0, and stranded it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = 'plugin "beancount.plugins.check_drained"\n'
ASSERTED = (
    PLUGIN
    + "2024-01-01 open Assets:Cash USD\n2024-01-01 open Equity:Opening USD\n2024-01-01 open Expenses:Food USD\n"
    + '2024-01-02 * "Seed"\n  Assets:Cash 100 USD\n  Equity:Opening -100 USD\n'
    + "2024-02-01 balance Assets:Cash 100 USD\n"
)
FLOW = (
    PLUGIN
    + "2024-01-01 open Assets:Cash USD\n2024-01-01 open Expenses:Food USD\n"
    + '2024-01-02 * "Meal"\n  Assets:Cash -7.75 USD\n  Expenses:Food 7.75 USD\n'
)


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", *args],
        env=env,
        cwd=tmp_path,
        input="",
        capture_output=True,
        text=True,
        timeout=120,
    )


def _close(tmp_path: Path, ledger: str, account: str, *flags: str) -> tuple[subprocess.CompletedProcess[str], bytes]:
    path = tmp_path / "main.bean"
    path.write_text(ledger)
    before = path.read_bytes()
    return _bea(
        tmp_path, "--json", "-f", str(path), "add", "close", "--account", account, "--date", "2024-02-01", *flags
    ), before


@pytest.mark.parametrize(
    ("ledger", "account", "amount"),
    [(ASSERTED, "Assets:Cash", "100 USD"), (FLOW, "Expenses:Food", "7.75 USD")],
    ids=["same-day-assertion", "flow-account"],
)
def test_a_funded_close_is_refused_and_leaves_the_ledger_alone(
    tmp_path: Path, ledger: str, account: str, amount: str
) -> None:
    result, before = _close(tmp_path, ledger, account)

    assert result.returncode == 1, result.stdout
    message = json.loads(result.stderr or result.stdout)["error"]["message"]
    assert f"{account} still holds {amount}" in message and "--force" in message
    assert (tmp_path / "main.bean").read_bytes() == before


def test_force_still_closes_a_funded_account(tmp_path: Path) -> None:
    result, _ = _close(tmp_path, ASSERTED, "Assets:Cash", "--force")

    assert result.returncode == 0, result.stderr
    assert _bea(tmp_path, "-f", str(tmp_path / "main.bean"), "check").returncode == 0


def test_a_drained_account_closes_without_force(tmp_path: Path) -> None:
    drained = ASSERTED.replace(
        "2024-02-01 balance Assets:Cash 100 USD\n",
        '2024-01-31 * "Move out"\n  Assets:Cash -100 USD\n  Expenses:Food 100 USD\n'
        "2024-02-01 balance Assets:Cash 0 USD\n",
    )

    result, _ = _close(tmp_path, drained, "Assets:Cash")

    assert result.returncode == 0, result.stderr
    assert _bea(tmp_path, "-f", str(tmp_path / "main.bean"), "check").returncode == 0


def test_the_plugin_still_speaks_for_an_account_it_covers(tmp_path: Path) -> None:
    unasserted = ASSERTED.replace("2024-02-01 balance Assets:Cash 100 USD\n", "")

    result, before = _close(tmp_path, unasserted, "Assets:Cash")

    assert result.returncode == 1, result.stdout
    assert "check_drained" in " ".join((result.stderr or result.stdout).split())
    assert (tmp_path / "main.bean").read_bytes() == before
