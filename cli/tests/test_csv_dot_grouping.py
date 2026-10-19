"""Dot-grouped thousands import whole, and ambiguous dot columns get a note (w5/753).

A column whose cells use only dot grouping never voted for comma decimals:
`1.650.000` was refused (exit 2, no decimal convention writes two decimal
points), while `-12.500` silently imported 1000x too small — `-12.500 ISK`
for an ISK account, whose currency has no minor unit.

A cell with two or more dot groups now votes for comma decimals; a dot-only
three-decimal column that could be either reads as decimals with a note
naming both readings; and `--csv decimal=comma|point` forces the reading.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from bea_engine.csv_mapper import (
    _dot_ambiguous_example,
    _resolve_decimal_comma,
    _separator_vote,
    parse_decimal,
)
from bea_engine.csv_mapper import (
    parse_mapping as engine_parse_mapping,
)
from bea_engine.protocol import UsageError
from cli.csv_mapper import parse_mapping as frontend_parse_mapping
from cli.errors import UsageError as FrontendUsageError

ROOT = Path(__file__).resolve().parents[1]

ISK_LEDGER = """option "operating_currency" "ISK"
2020-01-01 open Assets:Banki ISK
2020-01-01 open Expenses:Uncategorized
2020-01-01 open Income:Uncategorized
"""

USD_LEDGER = """option "operating_currency" "USD"
2020-01-01 open Assets:Cash USD
2020-01-01 open Expenses:Food USD
"""

A_CSV = """Date;Description;Amount
02.01.2026;Kaffi;-12.500
03.01.2026;Leiga;-185.000
04.01.2026;Laun;1.650.000
"""

B_CSV = """Date;Description;Amount
02.01.2026;Kaffi;-12.500
03.01.2026;Leiga;-185.000
04.01.2026;Laun;650.000
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
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.fixture
def isk_ledger(tmp_path: Path) -> Path:
    path = tmp_path / "isk.bean"
    path.write_text(ISK_LEDGER, encoding="utf-8")
    return path


@pytest.fixture
def usd_ledger(tmp_path: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(USD_LEDGER, encoding="utf-8")
    return path


def _import(
    tmp_path: Path,
    ledger: Path,
    body: str,
    csv: str | None,
    account: str,
    *extra: str,
    name: str = "bank.csv",
) -> subprocess.CompletedProcess[str]:
    source = tmp_path / name
    source.write_text(body, encoding="utf-8")
    argv = ["--json", "--no-input", "--file", str(ledger), "import", str(source)]
    if csv is not None:
        argv += ["--csv", csv]
    if account:
        argv += ["--account", account]
    return _bea(tmp_path, *argv, *extra)


def _payload(result: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(result.stdout)["data"]


def _banki_numbers(tmp_path: Path, ledger: Path) -> list[str]:
    result = _bea(
        tmp_path, "--json", "--file", str(ledger), "query", "SELECT number WHERE account = 'Assets:Banki' ORDER BY date"
    )
    assert result.returncode == 0, result.stderr
    return [row[0] for row in json.loads(result.stdout)["data"]["rows"]]


def test_two_dot_groups_import_as_whole_numbers(tmp_path: Path, isk_ledger: Path) -> None:
    preview = _import(tmp_path, isk_ledger, A_CSV, "auto", "Assets:Banki")
    assert preview.returncode == 0, preview.stderr
    assert "1650000" in preview.stdout

    applied = _import(tmp_path, isk_ledger, A_CSV, "auto", "Assets:Banki", "--apply")
    assert applied.returncode == 0, applied.stderr
    assert _banki_numbers(tmp_path, isk_ledger) == ["-12500", "-185000", "1650000"]
    check = _bea(tmp_path, "--file", str(isk_ledger), "check")
    assert check.returncode == 0, check.stdout + check.stderr


def test_dot_only_column_gets_a_note_naming_both_readings(tmp_path: Path, isk_ledger: Path) -> None:
    result = _import(tmp_path, isk_ledger, B_CSV, "auto", "Assets:Banki")
    assert result.returncode == 0, result.stderr
    notes = _payload(result)["notes"]
    assert any(
        "reads '-12.500' as -12.500 ISK" in note and "(-12500)" in note and "decimal=comma" in note for note in notes
    )
    # The reading itself is unchanged: decimals, as before.
    assert "650.000" in result.stdout


def test_decimal_comma_override_reads_whole_numbers_without_a_note(tmp_path: Path, isk_ledger: Path) -> None:
    result = _import(
        tmp_path, isk_ledger, B_CSV, "date=Date,amount=Amount,narration=Description,decimal=comma", "Assets:Banki"
    )
    assert result.returncode == 0, result.stderr
    assert "650000" in result.stdout
    assert not any("no minor unit" in note for note in _payload(result).get("notes", []))


def test_decimal_point_override_reads_decimals_without_a_note(tmp_path: Path, isk_ledger: Path) -> None:
    result = _import(
        tmp_path, isk_ledger, B_CSV, "date=Date,amount=Amount,narration=Description,decimal=point", "Assets:Banki"
    )
    assert result.returncode == 0, result.stderr
    assert "650.000" in result.stdout
    assert not any("no minor unit" in note for note in _payload(result).get("notes", []))


def test_bad_decimal_is_refused_naming_the_key(tmp_path: Path, isk_ledger: Path) -> None:
    before = isk_ledger.read_bytes()
    result = _import(
        tmp_path, isk_ledger, B_CSV, "date=Date,amount=Amount,narration=Description,decimal=comam", "Assets:Banki"
    )
    assert result.returncode == 2, result.stdout
    assert "Bad --csv decimal 'comam': use decimal=comma or decimal=point." in result.stderr
    assert isk_ledger.read_bytes() == before


def test_duplicate_decimal_is_refused(tmp_path: Path, isk_ledger: Path) -> None:
    result = _import(
        tmp_path,
        isk_ledger,
        B_CSV,
        "date=Date,amount=Amount,narration=Description,decimal=comma,decimal=point",
        "Assets:Banki",
    )
    assert result.returncode == 2, result.stdout
    assert "Duplicate --csv field 'decimal'." in result.stderr


def test_engine_parser_rejects_decimal_as_a_safety_net() -> None:
    with pytest.raises(UsageError, match=r"Unknown --csv field 'decimal'"):
        engine_parse_mapping("date=D,amount=A,narration=N,decimal=comma")


def _remember_comma(tmp_path: Path, isk_ledger: Path) -> None:
    first = _import(
        tmp_path, isk_ledger, B_CSV, "date=Date,amount=Amount,narration=Description,decimal=comma", "Assets:Banki"
    )
    assert first.returncode == 0, first.stderr


def test_recalled_decimal_replays_on_a_flag_free_run(tmp_path: Path, isk_ledger: Path) -> None:
    _remember_comma(tmp_path, isk_ledger)
    # Same headers, different file, no flags: the remembered convention replays.
    replay = _import(tmp_path, isk_ledger, B_CSV, None, "", name="next.csv")
    assert replay.returncode == 0, replay.stderr
    payload = _payload(replay)
    assert payload["config_source"] == "remembered --csv"
    assert payload["remembered"]["decimal"] == "comma"
    assert "650000" in replay.stdout
    assert any("decimal=comma" in note for note in payload["notes"])
    assert not any("no minor unit" in note for note in payload["notes"])


def test_keys_only_decimal_overrides_the_memory(tmp_path: Path, isk_ledger: Path) -> None:
    _remember_comma(tmp_path, isk_ledger)
    replay = _import(tmp_path, isk_ledger, B_CSV, "decimal=point", "Assets:Banki", name="next.csv")
    assert replay.returncode == 0, replay.stderr
    payload = _payload(replay)
    assert payload["remembered"]["decimal"] == "point"
    assert "650.000" in replay.stdout
    assert any("decimal=point" in note for note in payload["notes"])


def test_a_usd_dot_column_stays_silent(tmp_path: Path, usd_ledger: Path) -> None:
    body = "Date,Description,Amount\n2026-01-02,Kaffi,-12.500\n2026-01-03,Laun,650.000\n"
    result = _import(tmp_path, usd_ledger, body, "auto", "Assets:Cash")
    assert result.returncode == 0, result.stderr
    assert "650.000" in result.stdout
    assert not any("no minor unit" in note for note in _payload(result).get("notes", []))


def test_zero_led_two_groups_stay_refused_until_forced(tmp_path: Path, isk_ledger: Path) -> None:
    body = "Date;Description;Amount\n02.01.2026;Kaffi;-12.500\n03.01.2026;Zero;0.000.000\n"
    before = isk_ledger.read_bytes()
    refused = _import(tmp_path, isk_ledger, body, "auto", "Assets:Banki")
    assert refused.returncode == 2, refused.stdout
    assert "cannot parse amount '0.000.000'" in refused.stderr
    assert isk_ledger.read_bytes() == before

    forced = _import(
        tmp_path,
        isk_ledger,
        body,
        "date=Date,amount=Amount,narration=Description,decimal=comma",
        "Assets:Banki",
        "--apply",
    )
    assert forced.returncode == 0, forced.stderr
    assert _banki_numbers(tmp_path, isk_ledger) == ["-12500", "0"]


def test_two_groups_beside_point_decimals_are_refused(tmp_path: Path, isk_ledger: Path) -> None:
    body = "Date;Description;Amount\n02.01.2026;Kaffi;1,234.56\n03.01.2026;Laun;1.650.000\n"
    before = isk_ledger.read_bytes()
    result = _import(tmp_path, isk_ledger, body, "date=Date,amount=Amount,narration=Description", "Assets:Banki")
    assert result.returncode == 2, result.stdout
    assert "mix decimal conventions" in result.stderr
    assert isk_ledger.read_bytes() == before


class TestDotGroupingUnits:
    """The vote, the ambiguity scan, and both `decimal=` parsers, below the CLI."""

    @pytest.mark.parametrize(
        ("cells", "decimal_comma"),
        [
            (["1.650.000"], True),
            (["-12.500", "-185.000", "1.650.000"], True),
            (["1.234.567.890"], True),
            (["-12.500", "-185.000", "650.000"], False),
            (["0.000.000"], False),
        ],
    )
    def test_two_dot_groups_vote_comma_decimals(self, cells: list[str], decimal_comma: bool) -> None:
        assert _resolve_decimal_comma([(number, cell) for number, cell in enumerate(cells, 1)]) is decimal_comma

    def test_two_dot_groups_do_not_vote_alone(self) -> None:
        assert _separator_vote("12.500") is None
        assert _separator_vote("0.000.000") is None
        assert _separator_vote("1.650.000") == "eu"

    @pytest.mark.parametrize(
        ("cells", "example"),
        [
            (["-12.500", "-185.000", "650.000"], "-12.500"),
            (["12500", "650.000"], "650.000"),
            (["12500", "650.00"], None),
            (["12.500", "1,234.56"], None),
            (["12.500", "1,234"], None),
            (["1.650.000"], None),
            (["", "   "], None),
        ],
    )
    def test_dot_ambiguity_scan(self, cells: list[str], example: str | None) -> None:
        assert _dot_ambiguous_example(cells) == example

    @pytest.mark.parametrize(("value", "expected"), [("comma", "comma"), ("point", "point"), ("COMMA", "comma")])
    def test_parse_decimal_accepts_both_conventions(self, value: str, expected: str) -> None:
        assert parse_decimal(value) == expected

    def test_parse_decimal_refuses_anything_else(self) -> None:
        with pytest.raises(UsageError, match=r"Bad --decimal 'comam'"):
            parse_decimal("comam")

    def test_frontend_mapping_carries_decimal(self) -> None:
        mapping = frontend_parse_mapping("date=D,amount=A,narration=N,decimal=comma")
        assert mapping.decimal == "comma"
        assert frontend_parse_mapping("date=D,amount=A,narration=N").decimal is None

    def test_frontend_mapping_refuses_a_bad_decimal(self) -> None:
        with pytest.raises(FrontendUsageError, match=r"Bad --csv decimal 'comam'"):
            frontend_parse_mapping("date=D,amount=A,narration=N,decimal=comam")
