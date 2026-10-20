"""A plugin that rewrites a written transaction's header keeps import dedupe (w5/866).

w5/662 made the duplicate index require each transaction's plugin-free payee
and narration, so a local plugin that normalized either one hid every written
row from it: the identical export imported twice wrote the same payment
twice, exit 0, for a bank ID and for bea's own content ID alike.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
REWRITES = {
    "payee": 'entry._replace(payee="ACME")',
    "narration": 'entry._replace(narration="Cleaned description")',
    "unchanged": "entry",
}


def _bea(*args: str) -> dict[str, Any]:
    result = runner.invoke(app, ["--json", "--no-input", *args])
    assert result.exit_code == 0, result.output
    return dict(json.loads(result.stdout)["data"])


def _books(tmp_path: Path, rewrite: str) -> Path:
    module = f"normalize_{rewrite}"
    (tmp_path / f"{module}.py").write_text(
        "from beancount.core.data import Transaction\n"
        '__plugins__ = ["normalize"]\n'
        "def normalize(entries, options):\n"
        f"    return [{REWRITES[rewrite]} if isinstance(entry, Transaction) else entry for entry in entries], []\n"
    )
    root = tmp_path / "main.bean"
    root.write_text(
        'option "operating_currency" "USD"\n'
        'option "insert_pythonpath" "TRUE"\n'
        f'plugin "{module}"\n'
        "2026-01-01 open Assets:Checking USD\n"
        "2026-01-01 open Expenses:Uncategorized\n"
    )
    (tmp_path / "bank.csv").write_text(
        "Date,Payee,Description,Amount,Reference\n2026-02-01,Acme Ltd,Original description,-10.00,BANK-123\n"
    )
    return root


@pytest.mark.parametrize("rewrite", ["payee", "narration", "unchanged"])
@pytest.mark.parametrize("mapping", ["id=Reference", "generated"])
def test_the_identical_export_imports_once(tmp_path: Path, rewrite: str, mapping: str) -> None:
    root = _books(tmp_path, rewrite)
    csv = "date=Date,amount=Amount,payee=Payee,narration=Description"
    if mapping != "generated":
        csv += f",{mapping}"
    command = ["--file", str(root), "import", str(tmp_path / "bank.csv"), "--csv", csv]
    command += ["--account", "Assets:Checking", "--apply", "--duplicates", "skip"]

    first = _bea(*command)
    written = root.read_bytes()
    second = _bea(*command)

    assert (first["written"], first["rows"][0]["status"]) == (1, "new")
    assert (second["written"], second["duplicates"]) == (0, 1)
    assert second["rows"][0]["status"] == "duplicate"
    assert root.read_bytes() == written
    query = "SELECT count(*) AS n, sum(number) AS total WHERE account = 'Assets:Checking'"
    rows = _bea("--file", str(root), "query", query)["rows"]
    assert [(int(row[0]), str(row[1])) for row in rows] == [(1, "-10.00")]
