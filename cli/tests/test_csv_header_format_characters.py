"""Invisible header characters match, mappings normalize the same way, and listings escape (w5/716).

w5/531 dropped three zero-width characters from header cells, but direction
marks, ZWNJ/ZWJ, soft hyphens, and no-break spaces still printed invisibly in
the column listing while the advised mapping failed with "lacks". Mapping
names were only NFC-normalized, so a mapping naming a zero-width header
exactly as written was refused, and remembered records with raw headers no
longer matched.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Food USD
2026-01-01 open Expenses:Uncategorized USD
"""
ROW = b"2026-03-01,Coffee,-4.50\n"
MAPPING = "date=Date,amount=Amount,narration=Description"


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), "import", *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize(
    "header",
    [
        b"Date\xe2\x80\x8f,Description,Amount\n",
        b"Date\xe2\x80\x8e,Description,Amount\n",
        b"Date,Description\xe2\x80\x8c,Amount\n",
        b"Date\xe2\x80\x8d,Description,Amount\n",
        b"Date,Descrip\xc2\xadtion,Amount\n",
        b"Date\xc2\xa0,Description,Amount\n",
    ],
    ids=["rlm", "lrm", "zwnj", "zwj", "soft-hyphen", "nbsp-edge"],
)
@pytest.mark.parametrize("mapping", [(), ("--csv", MAPPING)], ids=["inferred", "explicit"])
def test_invisible_format_characters_import(tmp_path: Path, header: bytes, mapping: tuple[str, ...]) -> None:
    # nbsp-edge is a control: an edge NBSP was already stripped before w5/716,
    # and the space fold must keep it working.
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "bank.csv").write_bytes(header + ROW)

    result = _bea(tmp_path, "bank.csv", *mapping, "--account", "Assets:Checking", "--apply")

    assert result.returncode == 0, result.stdout + result.stderr
    assert '2026-03-01 ! "Coffee"' in (tmp_path / "main.bean").read_text()


@pytest.mark.parametrize("mapping", [(), ("--csv", "date=Booking Date,amount=Amount,narration=Description")])
def test_an_inner_nbsp_folds_to_a_plain_space(tmp_path: Path, mapping: tuple[str, ...]) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "bank.csv").write_bytes(b"Booking\xc2\xa0Date,Description,Amount\n" + ROW)

    result = _bea(tmp_path, "bank.csv", *mapping, "--account", "Assets:Checking", "--apply")

    assert result.returncode == 0, result.stdout + result.stderr
    assert '2026-03-01 ! "Coffee"' in (tmp_path / "main.bean").read_text()


def test_a_mapping_naming_the_zero_width_header_exactly_matches(tmp_path: Path) -> None:
    zwsp = chr(0x200B)
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "bank.csv").write_bytes(
        ("Date,Payee,Memo" + zwsp + ",Amount\n").encode("utf-8") + b"2026-03-01,Shop,Cash,-4.50\n"
    )

    result = _bea(
        tmp_path,
        "bank.csv",
        "--csv",
        "date=Date,amount=Amount,narration=Memo" + zwsp,
        "--account",
        "Assets:Checking",
        "--apply",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert '2026-03-01 ! "Cash"' in (tmp_path / "main.bean").read_text()


def test_a_record_remembered_with_raw_headers_still_matches(tmp_path: Path) -> None:
    zwsp = chr(0x200B)
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "bank.csv").write_bytes(b"Date,Description,Amount\n" + ROW)
    (tmp_path / "rules.toml").write_text('[[rule]]\nmatch = "coffee"\naccount = "Expenses:Food"\n')
    first = _bea(
        tmp_path, "bank.csv", "--csv", MAPPING, "--account", "Assets:Checking", "--rules", "rules.toml", "--apply"
    )
    assert first.returncode == 0, first.stdout + first.stderr
    (record,) = (tmp_path / "config" / "importers").glob("csv-*.json")
    # A record written before headers were normalized the same way keeps its
    # raw spellings; the live read must still find it.
    stored = json.loads(record.read_text())
    stored["sources"][0]["headers"] = ["Date", "Description" + zwsp, "Amount"]
    record.write_text(json.dumps(stored))

    second = _bea(tmp_path, "bank.csv", "--account", "Assets:Checking")

    assert second.returncode == 0, second.stdout + second.stderr
    assert "Using remembered settings for bank.csv" in second.stderr
    assert "Discarded remembered settings" not in second.stderr


def test_the_column_listing_escapes_what_still_does_not_print(tmp_path: Path) -> None:
    # A control character was already escaped by the error renderer; a line
    # separator passes it through raw, so the listing escapes it (w5/716).
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "bank.csv").write_bytes(b"Dat\x01e,Des\xe2\x80\xa8cription,Amount\n" + ROW)

    result = _bea(tmp_path, "bank.csv", "--account", "Assets:Checking")

    assert result.returncode == 2, result.stdout + result.stderr
    assert "Its columns are: Dat\\x01e, Des\\u2028cription, Amount." in result.stderr
    assert chr(1) not in result.stderr
    assert chr(0x2028) not in result.stderr


def test_the_engine_copy_normalizes_the_same_way(tmp_path: Path) -> None:
    from bea_engine.csv_mapper import header_signature, parse_mapping, read_header

    zwsp = chr(0x200B)
    (tmp_path / "bank.csv").write_bytes(b"Date\xe2\x80\x8f,Description,Amount\n" + ROW)

    assert read_header(tmp_path / "bank.csv") == ["Date", "Description", "Amount"]
    assert parse_mapping("date=Date,amount=Amount,narration=Description" + zwsp).columns["narration"] == "Description"
    assert header_signature(["Date", "Description" + zwsp, "Amount"]) == header_signature(
        ["Date", "Description", "Amount"]
    )


def test_shown_header_escapes_only_unprintables() -> None:
    from cli.csv_mapper import shown_header

    assert shown_header("Dat" + chr(1) + "e") == "Dat\\x01e"
    assert shown_header("Des" + chr(0x2028) + "cription") == "Des\\u2028cription"
    assert shown_header("Caf" + chr(0xE9)) == "Caf" + chr(0xE9)
