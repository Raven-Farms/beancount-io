"""A lone carriage return is not a line break in bea's own line table (w5/169).

Beancount's lexer numbers lines by `\\n` alone. `Path.read_text` translates
newlines first, so one raw `\\r` in a string — or `\\r\\r\\n` endings from a
double conversion — added a line the loader never counted. Every later
directive was then judged `generated`: `list --on-disk` hid it, `add price`
lost its conflict guard, and source-line diagnostics quoted the wrong line.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = (
    b"2024-01-01 open Assets:Cash USD\n"
    b"2024-01-01 open Equity:Open USD\n\n"
    b'2024-01-02 * "Shop" "pasted text"\n'
    b"  Assets:Cash   10.00 USD\n"
    b"  Equity:Open\n\n"
    b'2024-01-03 * "Cafe" "coffee"\n'
    b"  Assets:Cash   5.00 USD\n"
    b"  Equity:Open\n"
    b'2024-01-04 note Assets:Cash "hello"\n'
    b"2024-01-05 price USD 1.0 EUR\n"
)
LEDGERS = {
    "control": LEDGER,
    "cr-in-string": LEDGER.replace(b"pasted text", b"pasted\rtext"),
    "crlf": LEDGER.replace(b"\n", b"\r\n"),
    "crcrlf": LEDGER.replace(b"\n", b"\r\r\n"),
}
EXPECTED = {"open": 2, "transaction": 2, "note": 1, "price": 1}
PRICE_LINE = 12


def _bea(work: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(work / "config"),
        XDG_CACHE_HOME=str(work / "cache"),
        XDG_DATA_HOME=str(work / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=work,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
    )


@pytest.mark.parametrize("body", LEDGERS.values(), ids=LEDGERS.keys())
def test_every_written_directive_is_on_disk(tmp_path: Path, body: bytes) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_bytes(body)

    for kind, count in EXPECTED.items():
        listed = _bea(tmp_path, "--json", "--file", str(ledger), "list", kind)
        on_disk = _bea(tmp_path, "--json", "--file", str(ledger), "list", kind, "--on-disk")
        assert listed.returncode == 0, listed.stderr
        assert on_disk.returncode == 0, on_disk.stderr
        rows = json.loads(listed.stdout)["data"]
        assert len(rows) == count, kind
        assert not any(row.get("generated") for row in rows), (kind, rows)
        assert len(json.loads(on_disk.stdout)["data"]) == count, kind


@pytest.mark.parametrize("body", LEDGERS.values(), ids=LEDGERS.keys())
def test_add_price_refuses_a_conflicting_quote(tmp_path: Path, body: bytes) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_bytes(body)

    result = _bea(
        tmp_path,
        "--json",
        "--file",
        str(ledger),
        "add",
        "price",
        "--date",
        "2024-01-05",
        "--currency",
        "USD",
        "--amount",
        "1.2 EUR",
    )

    assert result.returncode == 4, result.stdout or result.stderr
    message = json.loads(result.stderr)["error"]["message"]
    assert "USD already has a 2024-01-05 price of 1.0 EUR" in message, message
    assert f"main.bean:{PRICE_LINE})" in message, message
    assert ledger.read_bytes() == body


def test_plugin_failure_names_its_own_line(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_bytes(
        b'; pasted\rcomment\n2024-01-01 open Assets:Cash USD\nplugin "beancount.plugins.no_such_plugin"\n'
    )

    result = _bea(tmp_path, "--json", "--file", str(ledger), "check")

    assert result.returncode == 1, result.stdout or result.stderr
    (detail,) = json.loads(result.stderr)["error"]["details"]
    assert detail.startswith(f"{ledger}:3: "), detail


def test_portable_document_warning_quotes_the_written_path(tmp_path: Path) -> None:
    books = tmp_path / "books"
    books.mkdir()
    (tmp_path / "invoice.pdf").write_bytes(b"%PDF-1.4 fake")
    ledger = books / "main.bean"
    ledger.write_bytes(
        b'; pasted\rcomment\n2024-01-01 open Expenses:Food USD\n2024-01-02 document Expenses:Food "../invoice.pdf"\n'
    )

    result = _bea(tmp_path, "--json", "--file", str(ledger), "check")

    assert result.returncode == 1, result.stdout or result.stderr
    (detail,) = json.loads(result.stderr)["error"]["details"]
    assert detail.startswith(f"{ledger}:3: Document path '../invoice.pdf' resolves to "), detail
