"""A `--json --allow-errors` write that fails still reports what the flag tolerated (w5/461).

USAGE promises `error.ledger_warnings` for every `--json` command that
tolerated loader errors before failing. `query` carried them; `add`, bulk
add and `import --apply` dropped them, so an agent never learned the ledger
was already broken.
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
2026-01-20 balance Assets:Cash 999 USD
"""
ROWS = json.dumps(
    [
        {
            "date": "2026-03-01",
            "narration": "X",
            "postings": [{"account": "Expenses:Nope", "amount": "1 USD"}, {"account": "Assets:Cash"}],
        }
    ]
)
CSV = "Date,Description,Amount\n2026-03-01,Coffee,-3.00\n"
COMMANDS = {
    "add": ["add", "transaction", "X", "--date", "2026-03-01", "-p", "Expenses:Nope 1 USD", "-p", "Assets:Cash"],
    "bulk": ["add", "transactions", "--from", "rows.json"],
    "import": [
        "import",
        "bank.csv",
        "--csv",
        "date=Date,narration=Description,amount=Amount,currency=USD",
        "--account",
        "Assets:Cash",
        "--apply",
    ],
}


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "rows.json").write_text(ROWS)
    (tmp_path / "bank.csv").write_text(CSV)
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
        [sys.executable, "-m", "cli.main", "--json", "-f", str(tmp_path / "main.bean"), *args, "--allow-errors"],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize(("command", "exit_code"), [("add", 1), ("bulk", 1), ("import", 4)])
def test_a_failed_write_carries_the_tolerated_errors(tmp_path: Path, command: str, exit_code: int) -> None:
    result = _bea(tmp_path, *COMMANDS[command])
    assert result.returncode == exit_code, result.stderr
    error = json.loads(result.stderr)["error"]
    warnings = error.get("ledger_warnings") or []
    assert any("main.bean:3: Balance failed for 'Assets:Cash'" in line for line in warnings), error
    assert (tmp_path / "main.bean").read_text() == LEDGER
