"""An undecodable importer record and an unopenable lock file are both named (w5/820).

A remembered-importer record holding invalid UTF-8 stopped a flag-free CSV
import with a pathless `'utf-8' codec can't decode byte 0xff`, exit 1, where
any other corrupt record is ignored with a note naming it (w5/592). A lock
file bea cannot open — mode 000, or root's after a `sudo bea` — was blamed on
the lock directory, which was writable (w5/593).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

ROOT = Path(__file__).resolve().parents[1]
LEDGER = (
    'option "operating_currency" "USD"\n2024-01-01 open Assets:Bank USD\n2024-01-01 open Expenses:Uncategorized USD\n'
)


def _record(ledger: Path, bea_config_dir: Path, prefix: str, content: bytes) -> Path:
    directory = bea_config_dir / "importers"
    directory.mkdir(parents=True, exist_ok=True)
    record = directory / f"{prefix}{hashlib.sha256(str(ledger.resolve()).encode()).hexdigest()}.json"
    record.write_bytes(content)
    return record


def _import(ledger: Path) -> tuple[int, str, str]:
    result = CliRunner().invoke(
        app,
        ["--no-input", "--file", str(ledger), "import", str(ledger.parent / "stmt.csv"), "--account", "Assets:Bank"],
    )
    return result.exit_code, result.stdout, " ".join(result.stderr.split())


@pytest.fixture
def ledger(tmp_path: Path, bea_config_dir: Path) -> Path:
    book = tmp_path / "main.bean"
    book.write_text(LEDGER)
    (tmp_path / "stmt.csv").write_text("Date,Amount,Description\n2024-02-01,-5.00,Coffee\n")
    return book


def test_an_importer_record_of_invalid_utf8_is_ignored_with_a_note_naming_it(
    ledger: Path, bea_config_dir: Path
) -> None:
    record = _record(ledger, bea_config_dir, "", b'{"config": "\xff\xfe"}')

    code, out, err = _import(ledger)

    assert code == 0, err
    assert f"The remembered importer record {record} is not valid; ignoring it." in err
    assert "codec" not in err
    assert "csv → Assets:Bank: 1 ready" in out


def test_a_deeply_nested_csv_record_is_no_memory(ledger: Path, bea_config_dir: Path) -> None:
    _record(ledger, bea_config_dir, "csv-", b"[" * 100_000 + b"]" * 100_000)

    code, out, err = _import(ledger)

    assert code == 0, err
    assert "recursion" not in err
    assert "csv → Assets:Bank: 1 ready" in out


def _add_price(tmp_path: Path, amount: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    command = ["--json", "-f", str(tmp_path / "main.bean"), "add", "price", "--commodity", "AAPL"]
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *command, "--amount", amount, "--date", "2024-01-05"],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
        stdin=subprocess.DEVNULL,
        check=False,
    )


@pytest.mark.skipif(os.name != "posix" or os.geteuid() == 0, reason="needs POSIX permissions that bind the user")
def test_a_lock_file_that_will_not_open_is_named(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text("2024-01-01 open Assets:Cash USD\n")
    first = _add_price(tmp_path, "100 USD")
    assert first.returncode == 0, first.stderr
    (lock,) = (tmp_path / "cache" / "bea" / "locks").glob("*.lock")
    before = ledger.read_text()
    lock.chmod(0)
    try:
        result = _add_price(tmp_path, "101 USD")
    finally:
        lock.chmod(0o600)

    assert result.returncode == 3, result.stderr
    error = json.loads(result.stderr)["error"]
    assert error["category"] == "auth"
    assert f"Cannot take the write lock: the lock file {lock} cannot be opened (Permission denied)." in error["message"]
    assert "Remove it, then retry. Nothing was written." in error["message"]
    assert "lock directory" not in error["message"]
    assert ledger.read_text() == before
