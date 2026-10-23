"""A stable ID is judged against the transactions the files spell (w5/881).

The ID index held the loaded entries, so whatever a plugin or the loader did
to a written transaction changed the answer: a filtered one was gone (written
again), a stripped price, an allocated template or a rounded wide negative
amount read as changed data (a false conflict, exit 4). A genuinely changed
source row must still conflict.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILTER_PLUGIN = """from beancount.core.data import Transaction
__plugins__ = ["run"]
def run(entries, options):
    return [e for e in entries if not isinstance(e, Transaction) or e.flag != "!"], []
"""
HEADER = 'option "operating_currency" "USD"\n'
CSV_IMPORT = [
    "import",
    "bank.csv",
    "--account",
    "Assets:Checking",
    "--default-account",
    "Expenses:Uncategorized",
    "--apply",
    "--duplicates",
    "skip",
]
OPENS = "2024-01-01 open Assets:Checking USD\n2024-01-01 open Expenses:Uncategorized\n"


def _bea(tmp_path: Path, *args: str, ledger: str = "main.bean") -> subprocess.CompletedProcess[str]:
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
        [sys.executable, "-m", "cli.main", "--json", "--no-input", "-f", str(tmp_path / ledger), *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def _written(result: subprocess.CompletedProcess[str]) -> int:
    assert result.returncode == 0, result.stderr or result.stdout
    return int(json.loads(result.stdout)["data"]["written"])


def _csv(tmp_path: Path, amount: str, reference: str = "BANK-123") -> list[str]:
    (tmp_path / "bank.csv").write_text(f"Date,Description,Amount,Reference\n2024-02-01,Coffee,{amount},{reference}\n")
    mapping = "date=Date,narration=Description,amount=Amount,decimal=point"
    return [*CSV_IMPORT, "--csv", f"{mapping},id=Reference" if reference else mapping]


def test_a_plugin_filtered_transaction_is_not_written_twice(tmp_path: Path) -> None:
    (tmp_path / "cleared_only.py").write_text(FILTER_PLUGIN)
    (tmp_path / "main.bean").write_text(HEADER + 'option "insert_pythonpath" "TRUE"\nplugin "cleared_only"\n' + OPENS)

    for reference in ("BANK-123", ""):
        args = _csv(tmp_path, "-10.00", reference)
        assert _written(_bea(tmp_path, *args)) == 1
        assert _written(_bea(tmp_path, *args)) == 0

    (tmp_path / "unfiltered.bean").write_text((tmp_path / "main.bean").read_text().replace('plugin "cleared_only"', ""))
    total = _bea(
        tmp_path,
        "query",
        "SELECT count(*), sum(number) WHERE account = 'Assets:Checking'",
        ledger="unfiltered.bean",
    )
    assert json.loads(total.stdout)["data"]["rows"] == [[2, "-20.00"]]


def test_a_wide_negative_amount_reimports_as_a_duplicate_and_a_change_conflicts(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(HEADER + OPENS)
    wide = "-12345678901.123456789012345678"
    args = _csv(tmp_path, wide, "wide-1")

    assert _written(_bea(tmp_path, *args)) == 1
    assert _written(_bea(tmp_path, *args)) == 0

    before = (tmp_path / "main.bean").read_bytes()
    changed = _bea(tmp_path, *_csv(tmp_path, wide[:-1] + "9", "wide-1"))
    assert changed.returncode == 4, changed.stdout
    assert (tmp_path / "main.bean").read_bytes() == before


CURRENCY_IMPORTER = """from pathlib import Path
from decimal import Decimal
from beancount.parser import parser

class Imp:
    def identify(self, file): return str(file).endswith(".txt")
    def account(self, file): return "Assets:CashEUR"
    def extract(self, file, existing_entries=None):
        rate = Decimal(Path(file).read_text().strip())
        text = ('2024-02-01 * "Bank" "FX conversion"\\n'
                '  bank_id: "fx-001"\\n'
                f'  Assets:CashEUR -100 EUR @ {rate} USD\\n'
                f'  Assets:CashUSD {100 * rate} USD\\n')
        entries, errors, _ = parser.parse_string(text)
        assert not errors, errors
        return entries

CONFIG = [Imp()]
"""


def test_a_native_id_survives_a_plugin_that_strips_the_price(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(
        'plugin "beancount.plugins.currency_accounts" "Equity:CurrencyAccounts"\n'
        + HEADER
        + "2024-01-01 open Assets:CashEUR EUR\n2024-01-01 open Assets:CashUSD USD\n"
    )
    (tmp_path / "importers.py").write_text(CURRENCY_IMPORTER)
    run = ["import", "bank.txt", "--config", "importers.py", "--apply", "--duplicates", "skip"]
    (tmp_path / "bank.txt").write_text("1.20\n")

    assert _written(_bea(tmp_path, *run)) == 1
    assert _written(_bea(tmp_path, *run)) == 0

    (tmp_path / "bank.txt").write_text("1.30\n")
    assert _bea(tmp_path, *run).returncode == 4


AMORTIZE_IMPORTER = """from pathlib import Path
from beancount.parser import parser
from beancount.core.data import Transaction

class Rows:
    def identify(self, file): return str(file).endswith(".schedule")
    def account(self, file): return "Assets:Prepaid"
    def extract(self, file, existing=None):
        entries, errors, options = parser.parse_string(Path(str(file)).read_text())
        assert not errors, errors
        rows = [entry for entry in entries if isinstance(entry, Transaction)]
        for entry in rows:
            entry.meta["bank_id"] = "insurance-2024"
        return rows

CONFIG = [Rows()]
"""


def test_a_native_id_template_reimports_beside_its_allocations(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(
        'plugin "fava.plugins.amortize_over"\n'
        + HEADER
        + "".join(
            f"2024-01-01 open {name} USD\n"
            for name in ("Assets:Cash", "Assets:Prepaid", "Equity:Opening", "Expenses:Insurance")
        )
        + '2024-01-01 * "Capital"\n  Assets:Cash 2000.00 USD\n  Equity:Opening -2000.00 USD\n'
        + '2024-01-02 * "Insurance payment"\n  Assets:Cash -1200.00 USD\n  Assets:Prepaid 1200.00 USD\n'
    )
    (tmp_path / "importer.py").write_text(AMORTIZE_IMPORTER)
    schedule = tmp_path / "amortization.schedule"
    template = (
        '2024-01-02 * "Amortize insurance"\n  amortize_months: 12\n'
        "  Assets:Prepaid -{total} USD\n  Expenses:Insurance {total} USD\n"
    )
    run = ["import", "amortization.schedule", "--config", "importer.py", "--apply", "--duplicates", "skip"]
    schedule.write_text(template.format(total="1200.00"))

    assert _written(_bea(tmp_path, *run)) == 1
    assert _written(_bea(tmp_path, *run)) == 0

    schedule.write_text(template.format(total="600.00"))
    assert _bea(tmp_path, *run).returncode == 4
