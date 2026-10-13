"""A ledger loading `nounused` can still gain an account through `bea` (w5/221).

`beancount.plugins.nounused` (also part of `pedantic`) reports an account that
is opened but not yet used. `add open` was refused because the open alone is
unused, `--allow-errors` did not help, and a transaction or import to the new
account was refused with a remedy naming that same `add open`. The open is now
staged with `--allow-errors`, like the first half of the pad flow, and each
remedy prints the command that works.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from bea_engine.ledger import adding

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """\
option "operating_currency" "USD"
{plugin}2024-01-01 commodity USD
2024-01-01 open Assets:Bank USD
2024-01-01 open Equity:Opening
2024-01-01 open Expenses:Food USD

2024-01-02 * "Opening"
  Assets:Bank  1000.00 USD
  Equity:Opening

2024-02-01 * "Lunch"
  Expenses:Food  12.50 USD
  Assets:Bank
"""
PLUGINS = ["beancount.plugins.nounused", "beancount.plugins.pedantic"]
OPEN = ["add", "open", "--account", "Expenses:Fuel", "--date", "2024-03-01", "-c", "USD"]
GAS = ["add", "transaction", "--date", "2024-03-01", "gas", "-p", "Expenses:Fuel 40.00 USD", "-p", "Assets:Bank"]


def _ledger(tmp_path: Path, plugin: str | None = PLUGINS[0]) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER.format(plugin=f'plugin "{plugin}"\n' if plugin else ""))
    return ledger


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
        COLUMNS="400",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--file", str(tmp_path / "main.bean"), *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _printed_open(stderr: str) -> list[str]:
    """The `bea add open …` line a refusal prints, as the arguments to run."""
    found = re.search(r"bea (add open --account \S+ --date [\w-]+(?: -c \w+)*(?: --allow-errors)?)", stderr)
    assert found, stderr
    return shlex.split(found.group(1).replace("YYYY-MM-DD", "2024-03-01"))


def _passes_check(tmp_path: Path) -> None:
    checked = _bea(tmp_path, "check")
    assert checked.returncode == 0, checked.stdout + checked.stderr


@pytest.mark.parametrize("plugin", PLUGINS)
def test_staged_open_then_first_transaction_leaves_a_valid_ledger(tmp_path: Path, plugin: str) -> None:
    ledger = _ledger(tmp_path, plugin)
    _passes_check(tmp_path)

    staged = _bea(tmp_path, *OPEN, "--allow-errors")

    assert staged.returncode == 0, staged.stderr
    assert "Added 1 open" in staged.stdout
    assert "Unused account 'Expenses:Fuel'" in staged.stderr and "Staged" in staged.stderr
    assert "2024-03-01 open Expenses:Fuel" in ledger.read_text()

    used = _bea(tmp_path, *GAS)

    assert used.returncode == 0, used.stderr
    assert '"gas"' in ledger.read_text()
    _passes_check(tmp_path)


def test_plain_open_is_refused_naming_the_flag_that_stages_it(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    before = ledger.read_text()

    refused = _bea(tmp_path, *OPEN)

    assert refused.returncode == 1
    assert "Unused account 'Expenses:Fuel'" in refused.stderr
    assert "--allow-errors" in refused.stderr
    assert ledger.read_text() == before


def test_missing_account_remedy_runs_as_printed(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    before = ledger.read_text()

    refused = _bea(tmp_path, *GAS)

    assert refused.returncode == 1 and ledger.read_text() == before
    remedy = _printed_open(refused.stderr)
    assert remedy[-1] == "--allow-errors"
    opened = _bea(tmp_path, *remedy)
    assert opened.returncode == 0, opened.stderr
    retried = _bea(tmp_path, *GAS)
    assert retried.returncode == 0, retried.stderr
    _passes_check(tmp_path)


def test_import_remedy_runs_as_printed_and_the_import_then_applies(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    before = ledger.read_text()
    (tmp_path / "s.csv").write_text("Date,Payee,Narration,Amount\n2024-03-01,Shell,gas,-40.00\n")
    (tmp_path / "r.toml").write_text('[[rule]]\nmatch = "shell"\naccount = "Expenses:Fuel"\n')
    importing = ["import", "s.csv", "--account", "Assets:Bank", "--rules", "r.toml", "--apply"]

    blocked = _bea(tmp_path, *importing)

    assert blocked.returncode == 4 and ledger.read_text() == before
    remedy = _printed_open(blocked.stderr)
    assert remedy == [*OPEN, "--allow-errors"]
    opened = _bea(tmp_path, *remedy)
    assert opened.returncode == 0, opened.stderr
    # The staged account is the one existing error the import itself clears.
    applied = _bea(tmp_path, *importing)
    assert applied.returncode == 0, applied.stderr
    assert "Expenses:Fuel    40.00 USD" in ledger.read_text()
    _passes_check(tmp_path)


def test_bulk_rows_clear_a_staged_open(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    assert _bea(tmp_path, *OPEN, "--allow-errors").returncode == 0
    row = {
        "date": "2024-03-01",
        "narration": "gas",
        "postings": [{"account": "Expenses:Fuel", "amount": "40.00 USD"}, {"account": "Assets:Bank"}],
    }

    result = adding.answer(ledger, "transactions", {"rows": [row], "partial": False})

    assert result["written"] == 1
    _passes_check(tmp_path)


def test_the_flag_exempts_only_the_open_being_staged(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    before = ledger.read_text()

    # Any other error a write introduces still refuses with the flag.
    unknown = _bea(tmp_path, *GAS, "--allow-errors")
    assert unknown.returncode == 1 and "would introduce 1 new ledger error" in unknown.stderr
    duplicate = _bea(tmp_path, "add", "open", "--account", "Assets:Bank", "--date", "2024-03-01", "--allow-errors")
    assert duplicate.returncode == 1, duplicate.stdout
    assert ledger.read_text() == before

    # A staged account still gates an unrelated strict write until it is used.
    assert _bea(tmp_path, *OPEN, "--allow-errors").returncode == 0
    lunch = ["add", "transaction", "--date", "2024-03-02", "lunch", "-p", "Expenses:Food 9 USD", "-p", "Assets:Bank"]
    gated = _bea(tmp_path, *lunch)
    assert gated.returncode == 1 and "Unused account 'Expenses:Fuel'" in gated.stderr
    assert '"lunch"' not in ledger.read_text()


def test_without_the_plugin_nothing_changes(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, None)

    refused = _bea(tmp_path, *GAS)
    assert refused.returncode == 1
    assert _printed_open(refused.stderr)[-1] == "2024-03-01"
    assert "nounused" not in refused.stderr

    opened = _bea(tmp_path, *OPEN)
    assert opened.returncode == 0, opened.stderr
    assert opened.stderr == ""
    assert "2024-03-01 open Expenses:Fuel" in ledger.read_text()
    _passes_check(tmp_path)
