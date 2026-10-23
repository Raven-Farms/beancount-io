"""A row filed under a parent account keeps which child each source posting hits (w5/912).

The generated ID and the content checks kept only amounts, so a payment to
`Assets:Broker:Two` was an exact duplicate of one to `Assets:Broker:One`, and
a native-ID correction that swapped the children's amounts was one too.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path

import pytest

from bea_engine.importing import _digest_import_id, _hash_base
from tests.test_import_source_facts import _bea, _written

LEDGER = (
    'option "operating_currency" "USD"\n2024-01-01 open Assets:Broker:One USD\n'
    "2024-01-01 open Assets:Broker:Two USD\n2024-01-01 open Income:Interest USD\n"
)
GENERATED = """from pathlib import Path
from beancount.parser import parser

class Imp:
    def identify(self, file): return str(file).endswith(".txt")
    def account(self, file): return "{account}"
    def extract(self, file, existing_entries=None):
        child = Path(file).read_text().strip()
        entries, errors, _ = parser.parse_string(
            '2024-02-01 * "Broker" "Interest"\\n'
            f'  Assets:Broker:{child} 1.00 USD\\n'
            '  Income:Interest -1.00 USD\\n')
        assert not errors, errors
        return entries

CONFIG = [Imp()]
"""
NATIVE = """import json
from pathlib import Path
from beancount.parser import parser

class Imp:
    def identify(self, file): return str(file).endswith(".json")
    def account(self, file): return "Assets:Broker"
    def extract(self, file, existing_entries=None):
        row = json.loads(Path(file).read_text())
        a, b = row["one"], row["two"]
        entries, errors, _ = parser.parse_string(
            '2024-02-01 * "Broker" "Interest"\\n'
            '  bank_id: "distribution-1"\\n'
            f'  Assets:Broker:One {a}.00 USD\\n'
            f'  Assets:Broker:Two {b}.00 USD\\n'
            f'  Income:Interest -{a+b}.00 USD\\n')
        assert not errors, errors
        return entries

CONFIG = [Imp()]
"""


def _totals(tmp_path: Path) -> dict[str, Decimal]:
    result = _bea(tmp_path, "query", "SELECT account, sum(number) GROUP BY account ORDER BY account")
    return {a: Decimal(str(n)) for a, n in json.loads(result.stdout)["data"]["rows"]}


def _generated(tmp_path: Path, account: str = "Assets:Broker") -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "importers.py").write_text(GENERATED.replace("{account}", account))
    (tmp_path / "one.txt").write_text("One\n")
    (tmp_path / "two.txt").write_text("Two\n")


def _run(name: str, *flags: str) -> list[str]:
    return ["import", name, "--config", "importers.py", "--duplicates", "include", *flags]


@pytest.mark.parametrize("order", [("one.txt", "two.txt"), ("two.txt", "one.txt")], ids=["one-first", "two-first"])
def test_two_children_under_one_parent_are_two_payments(tmp_path: Path, order: tuple[str, str]) -> None:
    _generated(tmp_path)

    for name in order:
        assert _written(_bea(tmp_path, *_run(name, "--apply"))) == 1

    assert _totals(tmp_path) == {
        "Assets:Broker:One": Decimal("1.00"),
        "Assets:Broker:Two": Decimal("1.00"),
        "Income:Interest": Decimal("-2.00"),
    }
    assert _bea(tmp_path, "check").returncode == 0
    for name in order:
        assert _written(_bea(tmp_path, *_run(name, "--apply"))) == 0


def test_an_older_child_blind_id_does_not_consume_the_other_child(tmp_path: Path) -> None:
    _generated(tmp_path)
    assert _written(_bea(tmp_path, *_run("one.txt", "--apply"))) == 1
    ledger = tmp_path / "main.bean"
    text = ledger.read_text()
    (found,) = re.findall(r'import-id: "(csv:sha256:[0-9a-f]+)"', text)
    # What the release before the child counted wrote for this row.
    legacy = _digest_import_id(_hash_base("2024-02-01", "1 USD", "BROKER|INTEREST", "Assets:Broker"), 1)
    ledger.write_text(text.replace(found, legacy))

    assert _written(_bea(tmp_path, *_run("one.txt", "--apply"))) == 0
    assert _written(_bea(tmp_path, *_run("two.txt", "--apply"))) == 1


def test_an_exact_child_account_is_unchanged(tmp_path: Path) -> None:
    _generated(tmp_path, account="Assets:Broker:One")

    assert _written(_bea(tmp_path, *_run("one.txt", "--apply"))) == 1
    assert _written(_bea(tmp_path, *_run("one.txt", "--apply"))) == 0


def _native(tmp_path: Path, one: int, two: int) -> list[str]:
    (tmp_path / "native.json").write_text(json.dumps({"one": one, "two": two}))
    return ["import", "native.json", "--config", "native.py", "--apply"]


def test_a_native_id_correction_that_swaps_the_children_is_a_conflict(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "native.py").write_text(NATIVE)

    assert _written(_bea(tmp_path, *_native(tmp_path, 1, 2))) == 1
    before = (tmp_path / "main.bean").read_bytes()

    swapped = _bea(tmp_path, *_native(tmp_path, 2, 1))

    assert swapped.returncode == 4, swapped.stdout
    assert (tmp_path / "main.bean").read_bytes() == before
    # The unchanged row still skips.
    assert _written(_bea(tmp_path, *_native(tmp_path, 1, 2))) == 0
