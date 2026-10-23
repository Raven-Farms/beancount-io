"""An importer posting with a cost but no units is refused, not written without its cost (w5/855).

Beancount's printer prints no cost beside missing units, so the lot was
dropped: the appended posting was a bare `Assets:Brokerage`, exit 0, and the
30 USD it balanced landed in the stock account.
"""

from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app
from tests.test_import_unwritable_rows_named import BASE, LEDGER

runner = CliRunner()


COSTED = textwrap.dedent("""
    from beancount.core.position import Cost, CostSpec

    def costed(units, cost):
        m = data.new_metadata("bank.txt", 1)
        src = data.Posting("Assets:Checking", amount.Amount(D("-30"), "USD"), None, None, None, None)
        dst = data.Posting("Assets:Brokerage", units, cost, None, None, None)
        return data.Transaction(m, day(3), "*", None, "Synthetic purchase", data.EMPTY_SET, data.EMPTY_SET, [src, dst])
""")


@pytest.mark.parametrize(
    "cost", ['Cost(D("10"), "USD", None, None)', 'CostSpec(D("10"), None, "USD", None, None, False)']
)
def test_a_cost_without_units_is_refused_not_dropped(tmp_path: Path, bea_config_dir: Path, cost: str) -> None:
    """The printer drops a cost beside missing units: 30 USD landed in the stock account, exit 0 (w5/855)."""
    (tmp_path / "main.bean").write_text(LEDGER + "2026-01-01 open Assets:Brokerage\n")
    (tmp_path / "bank.txt").write_text("x\n")
    (tmp_path / "base.py").write_text(BASE + COSTED)
    (tmp_path / "imp.py").write_text(f"from base import *\nCONFIG = [Base([costed(None, {cost})])]\n")
    before = (tmp_path / "main.bean").read_bytes()

    result = runner.invoke(
        app,
        ["--no-input", "--file", str(tmp_path / "main.bean"), "import", str(tmp_path / "bank.txt")]
        + ["--config", str(tmp_path / "imp.py"), "--apply"],
    )

    assert result.exit_code == 1, result.output
    assert (
        "Importer base row 1 cannot be written as a ledger entry: its Assets:Brokerage posting has a cost but no units"
        in " ".join(result.stderr.split())
    )
    assert (tmp_path / "main.bean").read_bytes() == before


def test_a_cost_with_units_still_writes_and_reloads(tmp_path: Path, bea_config_dir: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER + "2026-01-01 open Assets:Brokerage\n")
    (tmp_path / "bank.txt").write_text("x\n")
    (tmp_path / "base.py").write_text(BASE + COSTED)
    (tmp_path / "imp.py").write_text(
        "from base import *\n"
        'CONFIG = [Base([costed(amount.Amount(D("3"), "HOOL"), Cost(D("10"), "USD", None, None))])]\n'
    )
    base = ["--json", "--no-input", "--file", str(tmp_path / "main.bean")]

    applied = runner.invoke(
        app, [*base, "import", str(tmp_path / "bank.txt"), "--config", str(tmp_path / "imp.py"), "--apply"]
    )
    query = runner.invoke(app, [*base, "query", "SELECT units(position), cost(position) WHERE account ~ 'Brokerage'"])

    assert applied.exit_code == 0, applied.output
    assert re.search(r"Assets:Brokerage +3 HOOL \{10 USD\}", (tmp_path / "main.bean").read_text())
    assert query.exit_code == 0, query.output
    assert json.loads(query.stdout)["data"]["rows"] == [
        [{"number": "3", "currency": "HOOL"}, {"number": "30", "currency": "USD"}]
    ]
