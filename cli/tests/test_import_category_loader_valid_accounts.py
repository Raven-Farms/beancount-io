"""A CSV category cell naming an account the loader reads categorizes the row (w5/830).

`is_valid` is stricter than Beancount's loader, so a category naming an opened
`Expenses:Kค่า` or `Assets:Cash:中文` was called "not an account name" and the
row went to Uncategorized with `!`, while a rule naming the same account worked.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
ACCOUNTS = ["Expenses:Kค่า", "Assets:Cash:中文"]
LEDGER = "2024-01-01 open Assets:Bank USD\n2024-01-01 open Expenses:Uncategorized USD\n" + "".join(
    f"2024-01-01 open {name} USD\n" for name in ACCOUNTS
)


@pytest.mark.parametrize("account", ACCOUNTS)
def test_the_row_posts_to_the_named_account(tmp_path: Path, bea_config_dir: Path, account: str) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    (tmp_path / "bank.csv").write_text(f"Date,Description,Amount,Category\n2024-02-05,Market,-3.00,{account}\n")

    result = runner.invoke(
        app,
        ["--json", "--no-input", "--file", str(ledger), "import", str(tmp_path / "bank.csv")]
        + ["--csv", "date=Date,narration=Description,amount=Amount,category=Category", "--account", "Assets:Bank"]
        + ["--apply"],
    )

    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)["data"]
    assert data["written"] == 1
    assert not any("not an account name" in note for note in data["notes"])
    text = ledger.read_text()
    assert '2024-02-05 * "Market"' in text and account in text.split('"Market"', 1)[1]


def test_a_label_still_queues_for_review(tmp_path: Path, bea_config_dir: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    (tmp_path / "bank.csv").write_text("Date,Description,Amount,Category\n2024-02-05,Market,-3.00,Groceries\n")

    result = runner.invoke(
        app,
        ["--json", "--no-input", "--file", str(ledger), "import", str(tmp_path / "bank.csv")]
        + ["--csv", "date=Date,narration=Description,amount=Amount,category=Category", "--account", "Assets:Bank"],
    )

    assert result.exit_code == 0, result.output
    notes = json.loads(result.stdout)["data"]["notes"]
    assert any("not an account name ('Groceries')" in note for note in notes)
