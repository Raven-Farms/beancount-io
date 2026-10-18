"""A counter account equal to `--account` is refused or reviewed, never written (w5/468).

The row was written as `-100 USD` and `+100 USD` on the source account, with
exit 0: `bea check` passed and the bank movement vanished from the balance.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Assets:Savings USD
2026-01-01 open Expenses:Uncategorized USD
"""
EXPORT = "Date,Description,Amount\n2026-02-01,TRANSFER TO SAVINGS,-100.00\n2026-02-02,COFFEE,-3.00\n"
CATEGORIZED = (
    "Date,Description,Amount,Category\n"
    "2026-02-01,TRANSFER TO SAVINGS,-100.00,Assets:Checking\n"
    "2026-02-02,COFFEE,-3.00,Expenses:Uncategorized\n"
)


def _import(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    flags = [arg for arg in args if arg == "--json"]
    rest = [arg for arg in args if arg != "--json"]
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *flags, "-f", str(tmp_path / "main.bean"), "import", *rest],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _remembered(tmp_path: Path) -> list[Path]:
    return sorted((tmp_path / "config").glob("importers/*.json"))


def test_a_rule_naming_the_source_account_is_refused(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "s.csv").write_text(EXPORT)
    (tmp_path / "rules.toml").write_text('[[rule]]\nmatch = "transfer"\naccount = "Assets:Checking"\n')

    result = _import(tmp_path, "s.csv", "--account", "Assets:Checking", "--rules", "rules.toml", "--apply")

    assert result.returncode == 2, result.stdout + result.stderr
    assert "rule 1 (match 'transfer') posts to Assets:Checking, the --account being imported" in result.stderr
    assert (tmp_path / "main.bean").read_text() == LEDGER
    assert _remembered(tmp_path) == []


def test_a_default_account_naming_the_source_account_is_refused(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "s.csv").write_text(EXPORT)

    result = _import(
        tmp_path, "s.csv", "--account", "Assets:Checking", "--default-account", "Assets:Checking", "--apply"
    )

    assert result.returncode == 2, result.stdout + result.stderr
    assert "--default-account Assets:Checking is the --account being imported" in result.stderr
    assert (tmp_path / "main.bean").read_text() == LEDGER
    assert _remembered(tmp_path) == []


def test_a_category_cell_naming_the_source_account_goes_to_review(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "c.csv").write_text(CATEGORIZED)
    mapping = "date=Date,amount=Amount,narration=Description,category=Category"

    result = _import(tmp_path, "--json", "c.csv", "--account", "Assets:Checking", "--csv", mapping, "--apply")

    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)["data"]
    assert [row["rule"] for row in data["rows"]] == ["unmatched", "Expenses:Uncategorized"]
    assert any("1 row(s) carry the category Assets:Checking, the account being imported" in n for n in data["notes"])
    transfer = (tmp_path / "main.bean").read_text().split("\n\n")[1]
    assert transfer.startswith('2026-02-01 ! "TRANSFER TO SAVINGS"\n')
    assert transfer.splitlines()[-2:] == [
        "  Assets:Checking         -100.00 USD",
        "  Expenses:Uncategorized   100.00 USD",
    ]
