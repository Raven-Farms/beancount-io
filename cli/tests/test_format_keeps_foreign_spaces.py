"""Formatting never deletes a space Beancount reads as part of a name (w5/165).

Upstream's aligner separates account, number and currency with `\\s+`, which
also matches U+00A0 and U+3000; the lexer takes those as account characters.
With `--currency-column` upstream skips its whitespace-only check, so the
character was dropped, `format -i -c 40` exited 0, and two accounts became one.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPACES = {"no-break": " ", "ideographic": "　"}
WIDTHS = {"currency-column": ("-c", "40"), "automatic": (), "prefix-and-number": ("-w", "30", "-W", "12")}
QUERY = "SELECT account, sum(position) GROUP BY account ORDER BY account"


def _bea(work: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("BEA_") and key != "CI"}
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
        stdin=subprocess.DEVNULL,
        timeout=60,
    )


def _ledger(after_account: str, comment: str = "") -> str:
    return (
        'plugin "beancount.plugins.auto_accounts"\n\n'
        '2024-01-02 * "Lunch"\n'
        f"  Expenses:Food{after_account} 12.50 USD\n"
        "  Assets:Cash          -12.50 USD\n\n"
        '2024-01-03 * "Dinner"\n'
        f"  Expenses:Food   30.00 USD{comment}\n"
        "  Assets:Cash    -30.00 USD\n"
    )


def _accounts(work: Path, ledger: Path) -> list[str]:
    result = _bea(work, "--file", str(ledger), "query", QUERY)
    assert result.returncode == 0, result.stderr
    rows = result.stdout.decode().splitlines()[2:]
    return [row.split("  ")[0] for row in rows if row.strip()]


@pytest.mark.parametrize("widths", WIDTHS.values(), ids=WIDTHS.keys())
@pytest.mark.parametrize("char", SPACES.values(), ids=SPACES.keys())
def test_foreign_space_line_survives_and_accounts_stay_apart(
    tmp_path: Path, char: str, widths: tuple[str, ...]
) -> None:
    ledger = tmp_path / "main.bean"
    original = _ledger(char).encode()
    ledger.write_bytes(original)
    kept = original.split(b"\n")[3]
    before = _accounts(tmp_path, ledger)
    assert before == ["Assets:Cash", "Expenses:Food", f"Expenses:Food{char}"]
    exported = tmp_path / "formatted.bean"

    streamed = _bea(tmp_path, "format", *widths, str(ledger))
    written = _bea(tmp_path, "format", *widths, str(ledger), "-o", str(exported))
    checked = _bea(tmp_path, "format", *widths, "--check", str(ledger))
    assert ledger.read_bytes() == original
    applied = _bea(tmp_path, "format", *widths, "-i", str(ledger))

    for result in (streamed, written, applied):
        assert result.returncode == 0, result.stderr
    assert checked.returncode == 1, checked.stdout or checked.stderr
    formatted = ledger.read_bytes()
    assert (streamed.stdout, exported.read_bytes()) == (formatted, formatted)
    lines = formatted.split(b"\n")
    assert lines[3] == kept
    # The rest of the file is still aligned: every other amount shares a column.
    assert len({line.index(b" USD") for line in (lines[4], lines[7], lines[8])}) == 1
    assert formatted != original
    assert _accounts(tmp_path, ledger) == before
    assert _bea(tmp_path, "format", *widths, "--check", str(ledger)).returncode == 0


@pytest.mark.parametrize("widths", WIDTHS.values(), ids=WIDTHS.keys())
def test_ascii_space_control_still_aligns_every_posting(tmp_path: Path, widths: tuple[str, ...]) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(_ledger(" "), encoding="utf-8")
    before = _accounts(tmp_path, ledger)
    assert before == ["Assets:Cash", "Expenses:Food"]

    assert _bea(tmp_path, "format", *widths, "-i", str(ledger)).returncode == 0

    lines = ledger.read_bytes().split(b"\n")
    assert len({line.index(b" USD") for line in (lines[3], lines[4], lines[7], lines[8])}) == 1
    assert _accounts(tmp_path, ledger) == before


@pytest.mark.parametrize("char", SPACES.values(), ids=SPACES.keys())
def test_foreign_space_in_a_comment_does_not_exempt_the_posting(tmp_path: Path, char: str) -> None:
    ledger = tmp_path / "main.bean"
    comment = f" ; with{char}friends"
    ledger.write_text(_ledger(" ", comment), encoding="utf-8")

    assert _bea(tmp_path, "format", "-c", "40", "-i", str(ledger)).returncode == 0

    lines = ledger.read_text(encoding="utf-8").split("\n")
    assert lines[7].endswith("30.00 USD" + comment)
    assert len({line.index(" USD") for line in (lines[3], lines[4], lines[7], lines[8])}) == 1
