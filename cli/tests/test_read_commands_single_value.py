"""Read commands refuse two different values for one single-valued option (w5/381).

`list`, `report`, `balance` and `query` were plain Typer commands, which keep
the last of a repeated scalar option: `-a Food -a Rent` listed Rent alone and
`-t 2026-01 -t 2026-02` reported February, each with exit 0. `add` (w5/238),
`init` and `import` (w5/311) already refused that.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD
2026-01-01 open Expenses:Rent USD
2026-01-05 * "Grocer" #trip
  Expenses:Food  12.00 USD
  Assets:Cash
2026-01-06 * "Landlord" #trip
  Expenses:Rent  900.00 USD
  Assets:Cash
"""


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
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
        [sys.executable, "-m", "cli.main", "-f", "main.bean", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize(
    ("args", "named"),
    [
        (("list", "transaction", "-a", "Food", "-a", "Rent"), "-a 'Food' and -a 'Rent'"),
        (("list", "transaction", "--from-date", "2026-01-01", "--from-date", "2027-01-01"), "--from-date"),
        (("list", "open", "--limit", "1", "--limit", "3"), "--limit"),
        (("report", "income-statement", "-t", "2026-01", "-t", "2026-02"), "-t '2026-01' and -t '2026-02'"),
        (("balance", "-x", "units", "-x", "USD"), "-x 'units' and -x 'USD'"),
        (("query", "--format", "csv", "--format", "text", "SELECT account"), "--format"),
    ],
    ids=["list-account", "list-from-date", "list-limit", "report-time", "balance-conversion", "query-format"],
)
@pytest.mark.parametrize("json_mode", [False, True], ids=["text", "json"])
def test_conflicting_repeats_are_refused_naming_both(
    tmp_path: Path, args: tuple[str, ...], named: str, json_mode: bool
) -> None:
    result = _bea(tmp_path, *(["--json"] if json_mode else []), *args)

    assert result.returncode == 2, result.stdout + result.stderr
    message = json.loads(result.stderr)["error"]["message"] if json_mode else result.stderr
    assert "Conflicting values for one option" in message
    assert named in message


@pytest.mark.parametrize(
    "args",
    [
        ("list", "transaction", "-a", "Food", "-a", "Food"),
        ("list", "transaction", "--search", "Grocer", "--search", "trip"),
        ("list", "transaction", "--tag", "trip", "--tag", "trip"),
        ("report", "income-statement", "-t", "2026-01", "-t", "2026-01"),
    ],
    ids=["same-value-twice", "search-repeatable", "tag-repeatable", "same-time-twice"],
)
def test_repeatable_options_and_identical_repeats_still_work(tmp_path: Path, args: tuple[str, ...]) -> None:
    result = _bea(tmp_path, *args)

    assert result.returncode == 0, result.stderr
