"""Concurrent previews keep every file's chosen sign (w5/886).

Each preview built the header's whole sign map before the engine ran, so the
last to save replaced the others' entries with its stale snapshot and a
flag-free `--apply` then booked the lost files with the opposite sign, exit 0.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from cli.commands.import_ import _csv_record, _remember_csv, _sign_ledger_files, _source_sha256, _stored_sources

ROOT = Path(__file__).resolve().parents[1]
MAPPING = "date=Date,narration=Description,amount=Amount"
HEADERS = ["Date", "Description", "Amount"]


def _spec(sources: dict[str, str] | None = None) -> dict[str, Any]:
    return {
        "headers": HEADERS,
        "mapping": MAPPING,
        "source": "x.csv",
        "account": "Liabilities:QaCard",
        "rules": None,
        "default_account": None,
        "date_format": None,
        "delimiter": ",",
        "sign_ledger_files": sources or {},
        "sign_ledger_sha256": None,
    }


def _record(book: Path) -> dict[str, str]:
    (entry,) = _stored_sources(_csv_record(book, reading=True))
    return _sign_ledger_files(entry)


@pytest.fixture
def book(tmp_path: Path, bea_config_dir: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text("2024-01-01 open Liabilities:QaCard USD\n2024-01-01 open Expenses:Uncategorized USD\n")
    for name, amount in (("a", "10.00"), ("b", "20.00")):
        (tmp_path / f"{name}.csv").write_text(f"Date,Description,Amount\n2024-02-01,Charge {name},{amount}\n")
    return ledger


def test_a_stale_snapshot_does_not_drop_a_concurrent_files_sign(book: Path) -> None:
    a, b = book.parent / "a.csv", book.parent / "b.csv"
    # Both runs read the record while it was empty, as parallel previews do.
    assert _remember_csv(book, _spec(), [], sign_change=(a, True))
    assert _remember_csv(book, _spec(), [], sign_change=(b, True))

    assert set(_record(book)) == {_source_sha256(a), _source_sha256(b)}


def test_a_stale_snapshot_neither_resurrects_nor_drops_a_sign_removal(book: Path) -> None:
    a, b = book.parent / "a.csv", book.parent / "b.csv"
    assert _remember_csv(book, _spec(), [], sign_change=(a, True))
    stale = _spec({_source_sha256(a): "a.csv"})  # what a run reading it earlier still holds

    assert _remember_csv(book, stale, [], sign_change=(a, False))  # A moves to bank sign
    assert _remember_csv(book, stale, [], sign_change=(b, True))  # B's run saw A still signed

    assert set(_record(book)) == {_source_sha256(b)}


def test_four_parallel_previews_keep_four_signs(book: Path) -> None:
    root = book.parent
    for index in range(1, 5):
        (root / f"memory-{index}.csv").write_text(
            f"Date,Description,Amount\n2024-02-{index:02},Concurrent memory {index},{index * 10}.00\n"
        )
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=os.environ["BEA_CONFIG_DIR"],
        XDG_CACHE_HOME=str(root / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )

    def run(index: int, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "cli.main", "--json", "-f", str(book), "import", str(root / f"memory-{index}.csv"),
             "--account", "Liabilities:QaCard", *extra],
            env=env, cwd=root, input="", text=True, capture_output=True, timeout=120,
        )  # fmt: skip

    with ThreadPoolExecutor(max_workers=4) as pool:
        previews = list(pool.map(lambda i: run(i, "--csv", f"{MAPPING},sign=ledger"), range(1, 5)))
    assert [p.returncode for p in previews] == [0, 0, 0, 0], [p.stderr for p in previews]

    for index in range(1, 5):
        applied = run(index, "--apply")
        assert applied.returncode == 0, applied.stderr
        (row,) = json.loads(applied.stdout)["data"]["rows"]
        assert row["amount"] == f"-{index * 10}.00 USD"
