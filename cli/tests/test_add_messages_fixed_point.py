"""`add price` and `add balance` messages spell tiny amounts in fixed point (w5/201).

The conflict and `--pad-from` messages interpolated `str(Decimal)`, so a
satoshi-sized amount read `1E-8` — a spelling `bea` refuses as input, and not
what the user typed. They now match the `directive` echo and `list`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """\
2026-01-01 open Assets:Wallet
2026-01-01 open Equity:Opening

2026-01-02 * "Open"
  Assets:Wallet  0.00000001 BTC
  Equity:Opening

2026-02-10 price SHIB 0.00000001 BTC
2026-02-12 balance Assets:Wallet 0.00000001 BTC
"""

PADDED = """\
2026-01-01 open Assets:Wallet
2026-01-01 open Equity:Opening
2026-01-01 open Equity:Other

2026-01-02 * "Open"
  Assets:Wallet  0.00000001 BTC
  Equity:Opening

2026-01-03 * "Cash"
  Assets:Wallet  1000.00 USD
  Equity:Opening

2026-02-28 pad Assets:Wallet Equity:Opening
2026-03-01 balance Assets:Wallet 2000 USD
"""


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _ledger(tmp_path: Path, text: str = LEDGER) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(text, encoding="utf-8")
    return path


def _no_exponent(text: str) -> None:
    assert "E-8" not in text and "e-8" not in text, text


def test_price_conflict_names_both_quotes_in_fixed_point(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    before = ledger.read_bytes()
    price = ("add", "price", "--date", "2026-02-10", "-c", "SHIB", "--amount", "0.00000002 BTC")

    text = _bea(tmp_path, "--file", str(ledger), *price)
    as_json = _bea(tmp_path, "--json", "--file", str(ledger), *price)

    assert text.returncode == 2, text.stdout
    flat = " ".join(text.stderr.split())
    assert "price of 0.00000001 BTC" in flat
    assert "refusing 0.00000002 BTC" in flat
    _no_exponent(text.stderr)
    assert as_json.returncode == 2, as_json.stdout
    message = json.loads(as_json.stderr)["error"]["message"]
    assert "price of 0.00000001 BTC" in message
    assert "refusing 0.00000002 BTC" in message
    _no_exponent(message)
    assert ledger.read_bytes() == before


def test_the_notation_the_message_used_to_print_is_refused_as_input(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    before = ledger.read_bytes()

    done = _bea(
        tmp_path, "--file", str(ledger), "add", "price", "--date", "2026-02-11", "-c", "SHIB", "--amount", "1e-8 BTC"
    )

    assert done.returncode == 2, done.stdout
    assert "Scientific notation" in done.stderr
    assert ledger.read_bytes() == before


def test_the_refused_quote_can_be_fed_back_as_printed(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)

    done = _bea(
        tmp_path,
        "--json",
        "--file",
        str(ledger),
        "add",
        "price",
        "--date",
        "2026-02-10",
        "-c",
        "SHIB",
        "--amount",
        "0.00000002 BTC",
        "--force",
    )

    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["data"]["written"] == 1
    assert "2026-02-10 price SHIB 0.00000002 BTC" in " ".join(ledger.read_text(encoding="utf-8").split())


def test_balance_conflict_names_amounts_and_tolerance_in_fixed_point(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    before = ledger.read_bytes()

    toleranced = _bea(
        tmp_path,
        "--json",
        "--file",
        str(ledger),
        "add",
        "balance",
        "--date",
        "2026-02-12",
        "--account",
        "Assets:Wallet",
        "--amount",
        "0.00000002 ~ 0.00000001 BTC",
    )
    zero = _bea(
        tmp_path,
        "--file",
        str(ledger),
        "add",
        "balance",
        "--date",
        "2026-02-12",
        "--account",
        "Assets:Wallet",
        "--amount",
        "0.00000000 BTC",
    )

    assert toleranced.returncode == 2, toleranced.stdout
    message = json.loads(toleranced.stderr)["error"]["message"]
    assert "balance of 0.00000001 BTC" in message
    assert "refusing 0.00000002 ~ 0.00000001 BTC" in message
    _no_exponent(message)
    assert zero.returncode == 2, zero.stdout
    flat = " ".join(zero.stderr.split())
    assert "balance of 0.00000001 BTC" in flat
    assert "refusing 0.00000000 BTC" in flat
    _no_exponent(zero.stderr)
    assert ledger.read_bytes() == before


def test_pad_from_matching_book_warns_in_fixed_point(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)

    def pad(date: str) -> subprocess.CompletedProcess[str]:
        return _bea(
            tmp_path,
            "--json",
            "--file",
            str(ledger),
            "add",
            "balance",
            "--date",
            date,
            "--account",
            "Assets:Wallet",
            "--amount",
            "0.00000001 BTC",
            "--pad-from",
            "Equity:Opening",
        )

    recorded = pad("2026-02-12")
    written = pad("2026-02-13")

    for done, count in ((recorded, 0), (written, 1)):
        assert done.returncode == 0, done.stderr
        data = json.loads(done.stdout)["data"]
        assert data["written"] == count
        [warning] = data["warnings"]
        assert "Book balance already matches 0.00000001 BTC" in warning
        _no_exponent(warning)


def test_existing_pad_messages_name_the_inserted_amount_in_fixed_point(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, PADDED)
    before = ledger.read_bytes()

    def pad(source: str) -> subprocess.CompletedProcess[str]:
        return _bea(
            tmp_path,
            "--json",
            "--file",
            str(ledger),
            "add",
            "balance",
            "--date",
            "2026-03-01",
            "--account",
            "Assets:Wallet",
            "--amount",
            "0.00000003 BTC",
            "--pad-from",
            source,
        )

    refused = pad("Equity:Other")
    assert refused.returncode == 1, refused.stdout
    error = json.dumps(json.loads(refused.stderr)["error"])
    assert "insert 0.00000002 BTC" in error
    _no_exponent(error)
    assert ledger.read_bytes() == before

    written = pad("Equity:Opening")
    assert written.returncode == 0, written.stderr
    [warning] = json.loads(written.stdout)["data"]["warnings"]
    assert "inserting 0.00000002 BTC" in warning
    _no_exponent(warning)
