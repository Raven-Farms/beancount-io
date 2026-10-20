"""A migrated digest matches under any source prefix, not only the four bea listed (w5/601).

beancount-migrate's generic path writes `<source>:sha256:<digest>` for a
source it has no reference for (YNAB, Actual, a spreadsheet). `bea import`
matched only `csv:`, `mint:`, `monarch:` and `qbo:`, so the first bank
import after such a migration wrote every overlap row again, exit 0. A source
name with an underscore (`lunch_money:`) was still missed (w5/823).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
LEDGER = """option "operating_currency" "USD"

2026-03-04 open Assets:Checking USD
2026-03-04 open Expenses:Groceries USD
2026-03-04 open Expenses:Uncategorized USD

2026-03-08 * "Trader Joes" "TRADER JOES #123 SEATTLE WA"
  import-id: "{prefix}:sha256:9b811ad4dd24f37f"
  Assets:Checking     -54.20 USD
  Expenses:Groceries   54.20 USD
"""


@pytest.mark.parametrize("prefix", ["ynab", "actual", "my-sheet2", "lunch_money", "monarch", "csv"])
def test_a_migrated_row_is_an_exact_duplicate_under_any_source_prefix(
    tmp_path: Path, bea_config_dir: Path, prefix: str
) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER.format(prefix=prefix))
    source = tmp_path / "checking.csv"
    source.write_text("Date,Description,Amount\n2026-03-08,TRADER JOES #123 SEATTLE WA,-54.20\n")
    before = ledger.read_bytes()

    result = runner.invoke(
        app,
        ["--json", "--no-input", "--file", str(ledger), "import", str(source)]
        + ["--csv", "date=Date,narration=Description,amount=Amount", "--account", "Assets:Checking", "--apply"],
    )

    assert result.exit_code == 0, result.output
    (row,) = json.loads(result.stdout)["data"]["rows"]
    assert row["status"] == "duplicate"
    assert f"import-id {prefix}:sha256:9b811ad4dd24f37f is already in the ledger" in row["reason"]
    assert ledger.read_bytes() == before


def test_a_native_id_is_not_taken_for_a_digest(tmp_path: Path, bea_config_dir: Path) -> None:
    """Only `<source>:sha256:<16 hex>` is a digest: a bank's own `ref:9b81…` is not."""
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER.format(prefix="ynab").replace("ynab:sha256:", "ref:"))
    source = tmp_path / "checking.csv"
    source.write_text("Date,Description,Amount\n2026-03-08,TRADER JOES #123 SEATTLE WA,-54.20\n")

    result = runner.invoke(
        app,
        ["--json", "--no-input", "--file", str(ledger), "import", str(source)]
        + ["--csv", "date=Date,narration=Description,amount=Amount", "--account", "Assets:Checking"],
    )

    assert result.exit_code == 0, result.output
    (row,) = json.loads(result.stdout)["data"]["rows"]
    assert row["status"] != "duplicate"
