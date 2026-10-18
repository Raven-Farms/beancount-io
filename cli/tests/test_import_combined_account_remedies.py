"""An import row explains all missing/inactive accounts and relevant opening balances together (w5/692)."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
CSV = "Date,Description,Amount,Category\n2026-10-02,Payroll,1500.00,\n2026-09-28,Trader Joes,-55.10,\n"
IMPORTER = """import csv, datetime
from decimal import Decimal
from beancount.core import amount, data

class Bank:
    name = "synthetic-history"

    def identify(self, filepath):
        return filepath.endswith(".csv")

    def account(self, filepath):
        return "Assets:Checking"

    def extract(self, filepath, existing):
        entries = []
        with open(filepath, newline="") as stream:
            for line, row in enumerate(csv.DictReader(stream), start=2):
                categories = (row.get("Category") or "Expenses:Uncategorized").split("|")
                number = Decimal(row["Amount"])
                legs = [data.Posting("Assets:Checking", amount.Amount(number, "USD"), None, None, None, None)]
                legs += [data.Posting(name, amount.Amount(-number / len(categories), "USD"), None, None, None, None)
                         for name in categories]
                entries.append(data.Transaction(
                    data.new_metadata(filepath, line), datetime.date.fromisoformat(row["Date"]),
                    "*", None, row["Description"], frozenset(), frozenset(), legs))
        return entries

CONFIG = [Bank()]
"""


def _bea(directory: Path, *args: str, as_json: bool = True) -> subprocess.CompletedProcess[str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_") and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    env.update(
        BEA_CONFIG_DIR=str(directory / "config"),
        XDG_CACHE_HOME=str(directory / "cache"),
        XDG_DATA_HOME=str(directory / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_UPDATE_API_URL="http://127.0.0.1:9",
        BEA_TAP_FORMULA_URL="http://127.0.0.1:9/bea.rb",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *(["--json"] if as_json else []), "--no-input", *args],
        cwd=directory,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _init(directory: Path, *, date: str = "2026-10-17", opening_account: str | None = "Assets:Checking") -> Path:
    ledger = directory / "main.bean"
    opening = ["--opening-balance", f"{opening_account} 800"] if opening_account else []
    done = _bea(directory, "init", str(ledger), "--currency", "USD", "--date", date, *opening)
    assert done.returncode == 0, done.stdout + done.stderr
    return ledger


def _import(
    ledger: Path, mode: str = "csv", *, apply: bool = False, as_json: bool = True, allow_errors: bool = False
) -> subprocess.CompletedProcess[str]:
    source = ledger.parent / "history.csv"
    if mode == "importer":
        config = ledger.parent / "importers.py"
        config.write_text(IMPORTER)
        how = ["--config", str(config)]
    else:
        how = [
            "--csv",
            "date=Date,narration=Description,amount=Amount,category=Category",
            "--account",
            "Assets:Checking",
        ]
    return _bea(
        ledger.parent,
        "--file",
        str(ledger),
        "import",
        str(source),
        *how,
        *(["--apply"] if apply else []),
        *(["--allow-errors"] if allow_errors else []),
        as_json=as_json,
    )


def _data(done: subprocess.CompletedProcess[str], code: int = 0) -> dict[str, Any]:
    assert done.returncode == code, done.stdout + done.stderr
    payload = json.loads(done.stderr if code else done.stdout)
    if code:
        assert done.stdout == ""
        assert payload["error"]["category"] == "conflict" and payload["error"]["exit_code"] == 4
        return dict(payload["error"]["result"])
    return dict(payload["data"])


def _blocked_reasons(done: subprocess.CompletedProcess[str], *, as_json: bool, apply: bool) -> list[str]:
    if as_json:
        data = _data(done, 4 if apply else 0)
        assert data["ready"] == data["written"] == 0 and data["blocked"] == len(data["rows"])
        assert all(row["status"] == "blocked" and not row["include"] for row in data["rows"])
        return [row["reason"] for row in data["rows"]]
    assert done.returncode == (4 if apply else 0), done.stdout + done.stderr
    text = done.stderr if apply else done.stdout
    return re.findall(r"Row \d+(?: \(blocked\))?: (.+)", text)


def _location(path: Path, fragment: str) -> str:
    line = next(index for index, text in enumerate(path.read_text().splitlines(), start=1) if fragment in text)
    return f"{path}:{line}"


def _assert_opening_advice(reason: str, location: str) -> None:
    assert "Opening balances" in reason and "2026-10-17" in reason
    assert location in reason
    lowered = reason.lower()
    assert "move" in lowered and "restate" in lowered
    assert "before" in lowered and "history" in lowered and "twice" in lowered


@pytest.mark.parametrize("mode", ["csv", "importer"])
@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_history_before_real_init_names_both_late_accounts_and_the_opening_transaction(
    tmp_path: Path, mode: str, as_json: bool
) -> None:
    ledger = _init(tmp_path)
    (tmp_path / "history.csv").write_text(CSV)
    before = ledger.read_bytes()
    opening = _location(ledger, '* "Opening balances"')

    preview = _import(ledger, mode, as_json=as_json)
    reasons = _blocked_reasons(preview, as_json=as_json, apply=False)

    assert len(reasons) == 2, preview.stdout + preview.stderr
    for reason in reasons:
        for account in ("Assets:Checking", "Expenses:Uncategorized"):
            assert f"Account '{account}' opens 2026-10-17" in reason
            assert _location(ledger, f"open {account}") in reason
        assert reason.count("Re-date that open to 2026-09-28 or earlier.") == 2
        _assert_opening_advice(reason, opening)
    assert ledger.read_bytes() == before
    applied = _import(ledger, mode, apply=True, as_json=as_json)
    assert _blocked_reasons(applied, as_json=as_json, apply=True) == reasons
    assert ledger.read_bytes() == before


@pytest.mark.parametrize("mode", ["csv", "importer"])
@pytest.mark.parametrize("allow_errors", [False, True], ids=["strict", "allow-errors"])
def test_a_missing_counter_account_does_not_hide_a_late_source(tmp_path: Path, mode: str, allow_errors: bool) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text("2027-06-01 open Assets:Checking USD\n")
    (tmp_path / "history.csv").write_text("Date,Description,Amount,Category\n2026-03-01,History,-10,\n")
    before = ledger.read_bytes()

    reasons = _blocked_reasons(_import(ledger, mode, allow_errors=allow_errors), as_json=True, apply=False)

    assert len(reasons) == 1
    reason = reasons[0]
    assert "Account 'Expenses:Uncategorized' is not open." in reason
    assert "add open --account Expenses:Uncategorized --date 2026-03-01 -c USD" in reason
    assert "Account 'Assets:Checking' opens 2027-06-01" in reason
    assert "Re-date that open to 2026-03-01 or earlier." in reason
    assert "Opening balances" not in reason
    applied = _import(ledger, mode, apply=True, allow_errors=allow_errors)
    assert _blocked_reasons(applied, as_json=True, apply=True) == reasons
    assert ledger.read_bytes() == before


def test_multiple_late_and_closed_accounts_are_each_reported_once_even_with_repeated_postings(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(
        "2026-10-17 open Assets:Checking USD\n"
        "2026-11-01 open Expenses:Late USD\n"
        "2026-01-01 open Expenses:Closed USD\n"
        "2026-09-01 close Expenses:Closed\n"
    )
    (tmp_path / "history.csv").write_text(
        "Date,Description,Amount,Category\n2026-09-28,Split,-9,Expenses:Late|Expenses:Late|Expenses:Closed\n"
    )
    before = ledger.read_bytes()

    reasons = _blocked_reasons(_import(ledger, "importer"), as_json=True, apply=False)

    assert len(reasons) == 1
    reason = reasons[0]
    for account in ("Assets:Checking", "Expenses:Late", "Expenses:Closed"):
        assert reason.count(f"Account '{account}'") == 1, reason
    assert "opens 2026-10-17" in reason and "opens 2026-11-01" in reason and "was closed 2026-09-01" in reason
    assert _location(ledger, "close Expenses:Closed") in reason
    assert "Opening balances" not in reason
    assert _blocked_reasons(_import(ledger, "importer", apply=True), as_json=True, apply=True) == reasons
    assert ledger.read_bytes() == before


@pytest.mark.parametrize("mode", ["csv", "importer"])
@pytest.mark.parametrize("reverse", [False, True], ids=["newest-first", "oldest-first"])
def test_each_account_remedy_uses_its_earliest_date_across_the_whole_export(
    tmp_path: Path, mode: str, reverse: bool
) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(
        "2026-10-17 open Assets:Checking USD\n2026-11-01 open Expenses:First USD\n2026-12-01 open Expenses:Second USD\n"
    )
    rows = [
        "2026-10-02,Newer,-10,Expenses:First",
        "2026-09-28,Older,-9,Expenses:First",
        "2026-09-20,Oldest,-8,Expenses:Second",
    ]
    if reverse:
        rows.reverse()
    (tmp_path / "history.csv").write_text("Date,Description,Amount,Category\n" + "\n".join(rows) + "\n")
    before = ledger.read_bytes()

    data = _data(_import(ledger, mode))

    assert data["ready"] == 0 and data["blocked"] == 3
    for row in data["rows"]:
        remedies = dict(
            re.findall(r"Account '([^']+)' opens .*?Re-date that open to ([0-9-]+) or earlier\.", row["reason"])
        )
        counter = "Expenses:Second" if row["narration"] == "Oldest" else "Expenses:First"
        assert remedies == {
            "Assets:Checking": "2026-09-20",
            counter: "2026-09-20" if counter == "Expenses:Second" else "2026-09-28",
        }, row["reason"]
    assert ledger.read_bytes() == before


@pytest.mark.parametrize(
    "case", ["absent", "other-source", "different-date", "different-narration", "different-equity"]
)
def test_opening_balance_advice_requires_the_actual_init_entry_for_this_source(tmp_path: Path, case: str) -> None:
    ledger = _init(
        tmp_path,
        opening_account=None if case == "absent" else "Assets:Savings" if case == "other-source" else "Assets:Checking",
    )
    text = ledger.read_text()
    if case == "different-date":
        text = text.replace('2026-10-17 * "Opening balances"', '2026-10-20 * "Opening balances"')
    elif case == "different-narration":
        text = text.replace('"Opening balances"', '"Unrelated transfer"')
    elif case == "different-equity":
        text = text.replace("Equity:OpeningBalances", "Equity:Other")
    ledger.write_text(text)
    (tmp_path / "history.csv").write_text(CSV)
    before = ledger.read_bytes()

    reasons = _blocked_reasons(_import(ledger), as_json=True, apply=False)

    assert len(reasons) == 2
    for reason in reasons:
        assert "Account 'Assets:Checking'" in reason and "Account 'Expenses:Uncategorized'" in reason
        assert "Opening balances" not in reason
        assert "twice" not in reason
    assert ledger.read_bytes() == before


@pytest.mark.parametrize("mode", ["csv", "importer"])
def test_valid_history_after_init_needs_no_opening_balance_remedy_and_still_applies(tmp_path: Path, mode: str) -> None:
    ledger = _init(tmp_path, date="2026-01-01")
    (tmp_path / "history.csv").write_text(CSV)
    before = ledger.read_bytes()

    data = _data(_import(ledger, mode))

    assert data["ready"] == 2 and data["blocked"] == 0
    assert all(row["reason"] is None for row in data["rows"])
    assert ledger.read_bytes() == before
    applied = _data(_import(ledger, mode, apply=True))
    assert applied["written"] == 2 and ledger.read_bytes() != before
    checked = _bea(tmp_path, "--file", str(ledger), "check")
    assert checked.returncode == 0, checked.stdout + checked.stderr


def test_opening_balance_advice_points_to_the_written_included_transaction(tmp_path: Path) -> None:
    ledger = _init(tmp_path)
    included = tmp_path / "accounts.bean"
    ledger.rename(included)
    ledger.write_text('include "accounts.bean"\n')
    (tmp_path / "history.csv").write_text(CSV)
    before = {path: path.read_bytes() for path in (ledger, included)}

    reasons = _blocked_reasons(_import(ledger), as_json=True, apply=False)

    for reason in reasons:
        _assert_opening_advice(reason, _location(included, '* "Opening balances"'))
        assert ".bea-" not in reason.replace(str(tmp_path), "") and "candidate" not in reason
    assert _blocked_reasons(_import(ledger, apply=True), as_json=True, apply=True) == reasons
    assert {path: path.read_bytes() for path in before} == before
