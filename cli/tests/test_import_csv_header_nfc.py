"""`import --csv` finds a column whichever Unicode form names it (w5/204).

A mapping typed `narration=Descripción` composed was refused against a header
spelling the same name decomposed — "which nfc.csv lacks", over two names that
print identically — and a mapping remembered under one form was not recalled
for a header row or `--account` in the other.
"""

from __future__ import annotations

import os
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """\
option "operating_currency" "USD"
2024-01-01 open Assets:Bank USD
2024-01-01 open Assets:Café USD
2024-01-01 open Expenses:Uncategorized USD
"""
COMPOSED = "Descripción"
DECOMPOSED = "Descripción"
FORMS = [(COMPOSED, DECOMPOSED), (DECOMPOSED, COMPOSED), (COMPOSED, COMPOSED), (DECOMPOSED, DECOMPOSED)]
PREVIEW_ROW = "1    new     2024-01-02  abc                -5.00 USD"


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--file", str(tmp_path / "main.bean"), "import", *args],
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _export(tmp_path: Path, name: str, header: str) -> str:
    (tmp_path / "main.bean").write_text(LEDGER, encoding="utf-8")
    (tmp_path / name).write_text(f"Fecha,{header},Importe\n2024-01-02,abc,-5.00\n", encoding="utf-8")
    return str(tmp_path / name)


def _spec(column: str) -> str:
    return f"date=Fecha,narration={column},amount=Importe"


@pytest.mark.parametrize(("header", "typed"), FORMS)
def test_mapping_resolves_the_column_in_either_form(tmp_path: Path, header: str, typed: str) -> None:
    source = _export(tmp_path, "bank.csv", header)

    result = _bea(tmp_path, source, "--csv", _spec(typed), "--account", "Assets:Bank")

    assert result.returncode == 0, result.stderr
    assert PREVIEW_ROW in result.stdout


@pytest.mark.parametrize("header", [COMPOSED, DECOMPOSED])
def test_absent_column_is_still_refused(tmp_path: Path, header: str) -> None:
    source = _export(tmp_path, "bank.csv", header)

    unaccented = _bea(tmp_path, source, "--csv", _spec("Descripcion"), "--account", "Assets:Bank")
    lowercase = _bea(tmp_path, source, "--csv", _spec(COMPOSED.lower()), "--account", "Assets:Bank")

    assert unaccented.returncode == 2
    assert "The mapping names column 'Descripcion' for narration, which bank.csv lacks." in unaccented.stderr
    assert "Did you mean" not in unaccented.stderr
    # A case difference is still a different column, and still gets its hint.
    assert lowercase.returncode == 2
    assert f"Did you mean {COMPOSED!r}? Column names are case-sensitive." in lowercase.stderr


@pytest.mark.parametrize(("first", "second"), [(COMPOSED, DECOMPOSED), (DECOMPOSED, COMPOSED)])
def test_remembered_mapping_is_recalled_for_the_other_header_form(tmp_path: Path, first: str, second: str) -> None:
    seeded = _bea(tmp_path, _export(tmp_path, "one.csv", first), "--csv", _spec(first), "--account", "Assets:Bank")
    assert seeded.returncode == 0, seeded.stderr

    recalled = _bea(tmp_path, _export(tmp_path, "two.csv", second))

    assert recalled.returncode == 0, recalled.stderr
    assert "Using settings remembered from one.csv for two.csv" in recalled.stderr
    assert PREVIEW_ROW in recalled.stdout


@pytest.mark.parametrize("form", ["NFC", "NFD"])
def test_remembered_mapping_is_recalled_for_the_other_account_form(tmp_path: Path, form: str) -> None:
    other = "NFD" if form == "NFC" else "NFC"
    source = _export(tmp_path, "bank.csv", COMPOSED)
    account = unicodedata.normalize(form, "Assets:Café")
    seeded = _bea(tmp_path, source, "--csv", _spec(COMPOSED), "--account", account)
    assert seeded.returncode == 0, seeded.stderr

    recalled = _bea(tmp_path, source, "--account", unicodedata.normalize(other, account))
    # Naming the account again must replace its entry, not file a second one
    # that would make the flag-free run ambiguous.
    _bea(tmp_path, source, "--csv", _spec(COMPOSED), "--account", unicodedata.normalize(other, account))
    flag_free = _bea(tmp_path, source)

    assert recalled.returncode == 0, recalled.stderr
    assert "Using remembered settings for bank.csv" in recalled.stderr
    assert PREVIEW_ROW in recalled.stdout
    assert flag_free.returncode == 0, flag_free.stderr
    assert "matches multiple source accounts" not in flag_free.stderr


def test_another_account_does_not_recall_the_mapping(tmp_path: Path) -> None:
    source = _export(tmp_path, "bank.csv", "Memo")
    seeded = _bea(tmp_path, source, "--csv", _spec("Memo"), "--account", "Assets:Café")
    assert seeded.returncode == 0, seeded.stderr

    other = _bea(tmp_path, source, "--account", "Assets:Bank")

    assert other.returncode == 2
    assert "remembered" not in other.stderr.replace("is remembered for this ledger", "")
