"""A booked cost keeps an empty lot label when printed (w5/915).

Upstream's printer drops a falsy label, and the repair covered `CostSpec`
only; a loaded ledger holds booked `Cost` objects, so `query PRINT` merged the
`""` lot into the unlabelled one in the exported copy, and a native importer
returning a `Cost` did the same on write.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from tests.test_import_source_facts import ROOT, _bea, _written


def _plain(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """A run without the global `--json`, for the commands that choose their own format."""
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
        [sys.executable, "-m", "cli.main", "--no-input", "-f", str(tmp_path / "main.bean"), *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


LEDGER = (
    'option "operating_currency" "USD"\n2024-01-01 open Assets:Cash USD\n2024-01-01 open Assets:Stock HOOL\n'
    '2024-01-01 open Equity:Opening USD\n2024-01-01 * "Capital"\n  Assets:Cash 1000 USD\n  Equity:Opening -1000 USD\n'
    '2024-02-01 * "Existing unlabelled"\n  Assets:Stock 1 HOOL {100 USD}\n  Assets:Cash -100 USD\n'
)


def _lots(tmp_path: Path, ledger: str) -> list[tuple[str, str]]:
    result = _bea(tmp_path, "query", "SELECT sum(position) WHERE account = 'Assets:Stock'", ledger=ledger)
    cell = json.loads(result.stdout)["data"]["rows"][0][0]
    return sorted((str(pos["units"]["number"]), str(pos["cost"]["label"])) for pos in cell)


@pytest.mark.parametrize("flags", [["--format", "beancount"], []], ids=["beancount", "default"])
def test_print_export_keeps_the_empty_label(tmp_path: Path, flags: list[str]) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    for label, name in (('""', "Empty"), ('"lot-a"', "Named")):
        added = _bea(
            tmp_path, "add", "transaction", name, "--date", "2024-02-01",
            "-p", f"Assets:Stock 1 HOOL {{100 USD, {label}}}", "-p", "Assets:Cash -100 USD",
        )  # fmt: skip
        assert added.returncode == 0, added.stderr
    before = (tmp_path / "main.bean").read_bytes()

    exported = _plain(tmp_path, "query", "PRINT", *flags, "-o", str(tmp_path / "flat.bean"))
    assert exported.returncode == 0, exported.stderr

    assert (tmp_path / "main.bean").read_bytes() == before
    flat = (tmp_path / "flat.bean").read_text()
    assert '{100 USD, 2024-02-01, ""}' in flat and '{100 USD, 2024-02-01, "lot-a"}' in flat
    assert _bea(tmp_path, "check", ledger="flat.bean").returncode == 0
    assert _lots(tmp_path, "flat.bean") == _lots(tmp_path, "main.bean")


IMPORTER = """from datetime import date
from decimal import Decimal
from beancount.core.amount import Amount
from beancount.core.data import Posting, Transaction
from beancount.core.position import Cost

class Imp:
    def identify(self, file): return str(file).endswith(".txt")
    def account(self, file): return "Assets:Stock"
    def extract(self, file, existing_entries=None):
        day = date(2024, 2, 1)
        return [Transaction({}, day, "*", None, "Imported trade", frozenset(), frozenset(), [
            Posting("Assets:Stock", Amount(Decimal("1"), "HOOL"), Cost(Decimal("100"), "USD", day, ""),
                    None, None, None),
            Posting("Assets:Cash", Amount(Decimal("-100"), "USD"), None, None, None, None),
        ])]

CONFIG = [Imp()]
"""


def test_a_native_importer_cost_keeps_its_empty_label(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "importers.py").write_text(IMPORTER)
    (tmp_path / "bank.txt").write_text("synthetic\n")

    applied = _bea(tmp_path, "import", "bank.txt", "--config", "importers.py", "--apply")

    assert _written(applied) == 1
    assert '{100 USD, 2024-02-01, ""}' in (tmp_path / "main.bean").read_text()
    assert _lots(tmp_path, "main.bean") == [("1", ""), ("1", "None")]
    assert _bea(tmp_path, "check").returncode == 0


def test_unlabelled_and_named_costs_print_as_before(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)

    exported = _plain(tmp_path, "query", "PRINT", "--format", "beancount", "-o", str(tmp_path / "flat.bean"))

    assert exported.returncode == 0, exported.stderr
    assert "{100 USD, 2024-02-01}" in (tmp_path / "flat.bean").read_text()
    assert Decimal("1") == Decimal(_lots(tmp_path, "flat.bean")[0][0])
