"""Imports run side by side all keep their remembered CSV mapping (w5/214).

The record was read, extended and replaced with no lock, so of two previews
finishing together the later replace dropped the earlier entry. A header
shared by checking and savings then looked like one account's, and a flag-free
`--apply` booked the other export's rows there instead of refusing.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

import pytest

from cli.commands import import_

ROOT = Path(__file__).resolve().parents[1]
HEADERS = ["Date", "Description", "Amount"]
MAPPING = "date=Date,amount=Amount,narration=Description"
ACCOUNTS = ["Assets:Checking", "Assets:Savings", "Assets:Brokerage", "Assets:Cash"]
LEDGER = (
    'option "operating_currency" "USD"\n'
    + "".join(f"2026-01-01 open {account} USD\n" for account in ACCOUNTS)
    + "2026-01-01 open Expenses:Uncategorized USD\n"
)


def _record(config: Path) -> Path:
    (record,) = (config / "importers").glob("csv-*.json")
    return record


def _remembered_accounts(record: Path) -> list[str]:
    return sorted(entry["account"] for entry in json.loads(record.read_text())["sources"])


def test_overlapping_writers_each_keep_their_entry(
    tmp_path: Path, bea_config_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    read_stored = import_._stored_sources
    both_have_read = threading.Barrier(2, timeout=0.5)

    def read_then_meet_the_other_writer(record: Path) -> list[dict[str, Any]]:
        sources = read_stored(record)
        try:
            # Unlocked, both writers get here holding the same old contents.
            # Locked, the second is still waiting and the barrier times out.
            both_have_read.wait()
        except threading.BrokenBarrierError:
            pass
        return sources

    monkeypatch.setattr(import_, "_stored_sources", read_then_meet_the_other_writer)
    results: list[bool] = []
    writers = [
        threading.Thread(
            target=lambda account=account: results.append(
                import_._remember_csv(ledger, {"headers": HEADERS, "account": account, "mapping": MAPPING}, [])
            )
        )
        for account in ACCOUNTS[:2]
    ]
    for writer in writers:
        writer.start()
    for writer in writers:
        writer.join(timeout=30)

    assert results == [True, True]
    assert _remembered_accounts(_record(bea_config_dir)) == ["Assets:Checking", "Assets:Savings"]


def test_one_writer_after_another_keeps_both_entries(tmp_path: Path, bea_config_dir: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)

    for account in ACCOUNTS[:2]:
        assert import_._remember_csv(ledger, {"headers": HEADERS, "account": account, "mapping": MAPPING}, [])
    # Re-remembering an account replaces its entry rather than adding one.
    assert import_._remember_csv(ledger, {"headers": HEADERS, "account": ACCOUNTS[0], "mapping": MAPPING}, [])

    assert _remembered_accounts(_record(bea_config_dir)) == ["Assets:Checking", "Assets:Savings"]


def test_parallel_previews_remember_every_account_and_apply_refuses_to_choose(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    config = tmp_path / "config"
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(config),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    bea = [sys.executable, "-m", "cli.main", "--file", str(ledger), "import"]
    sources = []
    for index, account in enumerate(ACCOUNTS):
        source = tmp_path / f"export{index}.csv"
        source.write_text(f"Date,Description,Amount\n2026-02-0{index + 1},Row {index},{index + 1}.25\n")
        sources.append((source, account))

    previews = [
        subprocess.Popen(
            [*bea, str(source), "--account", account],
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for source, account in sources
    ]
    for preview in previews:
        _, stderr = preview.communicate(timeout=120)
        assert preview.returncode == 0, stderr

    assert _remembered_accounts(_record(config)) == sorted(ACCOUNTS)
    before = ledger.read_text()
    applied = subprocess.run(
        [*bea, str(sources[1][0]), "--apply"],
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert applied.returncode == 2, applied.stderr
    assert f"multiple source accounts: {', '.join(sorted(ACCOUNTS))}" in " ".join(applied.stderr.split())
    assert ledger.read_text() == before
