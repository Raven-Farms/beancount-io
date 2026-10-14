"""Tables give nonspacing marks no column, and truncation keeps a cluster whole (w5/246).

The width measure asked for the canonical combining class, which is 0 for many
marks that still draw onto the character before them: Thai and Devanagari
vowel signs, and (before they were covered as format characters) the emoji
variation selector and the zero-width joiner. A Thai or Hindi payee was padded
short, so every column to its right shifted left, and a narrow terminal could
cut a family emoji after its joiner.

Offsets are measured with a rule written out here rather than with
`display_width`, so the test states the property instead of echoing the code.
"""

from __future__ import annotations

import fcntl
import os
import pty
import re
import struct
import subprocess
import sys
import termios
import unicodedata
from pathlib import Path

import pytest

from cli.output import display_width, truncate

ROOT = Path(__file__).resolve().parents[1]

PLAIN = "Plain Cafe"
THAI = "ร้านก๋วยเตี๋ยวป้าศรี"
HINDI = "किराना दुकान"
SELECTORS = "☕️❤️✈️ Trip"
FAMILY = "\U0001f468‍\U0001f469‍\U0001f467‍\U0001f466 Family dinner out"
PAYEES = [PLAIN, THAI, HINDI, SELECTORS, FAMILY]
JOINER = "‍"


def _width(text: str) -> int:
    """East Asian wide = 2; nonspacing, enclosing, format and skin tone = 0; the rest = 1."""
    total = 0
    for char in text:
        if unicodedata.category(char) in {"Mn", "Me", "Cf"} or "\U0001f3fb" <= char <= "\U0001f3ff":
            continue
        total += 2 if unicodedata.east_asian_width(char) in "WF" else 1
    return total


def _ledger(tmp_path: Path) -> Path:
    text = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Checking USD\n2026-01-01 open Expenses:Food USD\n'
    for day, payee in enumerate(PAYEES, start=2):
        text += f'2026-01-0{day} * "{payee}" "lunch"\n  Expenses:Food  {day - 1}.00 USD\n  Assets:Checking\n'
    ledger = tmp_path / "main.bean"
    ledger.write_text(text, encoding="utf-8")
    return ledger


def _env(tmp_path: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k not in {"COLUMNS", "LINES", "CI"}}
    env.update(
        HOME=str(tmp_path / "home"),
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        PYTHONIOENCODING="utf-8",
        TERM="xterm-256color",
        NO_COLOR="1",
    )
    return env


def _on_terminal(tmp_path: Path, columns: int) -> dict[str, str]:
    """`bea list transaction -a Food` on a real pseudo-terminal of this width, one row per payee."""
    ledger = _ledger(tmp_path)
    master, slave = pty.openpty()
    try:
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, columns, 0, 0))
        process = subprocess.Popen(
            [sys.executable, "-m", "cli.main", "--file", str(ledger), "list", "transaction", "-a", "Food"],
            env=_env(tmp_path),
            cwd=tmp_path,
            stdin=subprocess.DEVNULL,
            stdout=slave,
            stderr=subprocess.PIPE,
        )
        os.close(slave)
        slave = -1
        chunks = []
        while True:
            try:
                chunk = os.read(master, 4096)
            except OSError:  # Linux reports the closed slave as EIO, macOS as EOF.
                break
            if not chunk:
                break
            chunks.append(chunk)
        _, stderr = process.communicate(timeout=60)
    finally:
        if slave >= 0:
            os.close(slave)
        os.close(master)
    assert process.returncode == 0, stderr.decode()
    lines = b"".join(chunks).decode().replace("\r\n", "\n").splitlines()
    rows = {}
    for day, payee in enumerate(PAYEES, start=2):
        (rows[payee],) = [line for line in lines if line.startswith(f"2026-01-0{day}")]
    return rows


class TestDisplayWidth:
    @pytest.mark.parametrize(
        ("text", "columns"),
        [
            pytest.param(PLAIN, 10, id="ascii-control"),
            pytest.param("é", 1, id="combining-acute-control"),
            pytest.param("กิ", 1, id="thai-vowel-sign"),
            pytest.param("ก้", 1, id="thai-tone-mark-control"),
            pytest.param("दु", 1, id="devanagari-vowel-sign"),
            # U+093F is a spacing mark (Mc): it does take its own cell.
            pytest.param("कि", 2, id="devanagari-spacing-mark-control"),
            pytest.param("a⃝", 1, id="enclosing-circle"),
            pytest.param("\U0001f44b\U0001f3fd", 2, id="skin-tone-modifier"),
            pytest.param(THAI, _width(THAI), id="thai-payee"),
            pytest.param(HINDI, _width(HINDI), id="hindi-payee"),
            pytest.param(SELECTORS, _width(SELECTORS), id="variation-selectors"),
            pytest.param(FAMILY, _width(FAMILY), id="joined-family"),
        ],
    )
    def test_counts_terminal_columns(self, text: str, columns: int) -> None:
        assert display_width(text) == columns


class TestTruncate:
    def test_ascii_control_is_cut_to_the_width(self) -> None:
        assert truncate("Amazon Marketplace", 10) == "Amazon ..."

    @pytest.mark.parametrize("width", range(3, 12))
    def test_never_ends_on_a_joiner(self, width: int) -> None:
        kept = truncate(FAMILY, width).removesuffix("...")

        assert not kept.endswith(JOINER)
        # The family is one cluster: all four people or none of them.
        assert kept in {"", FAMILY[:7]}
        assert _width(kept) <= max(0, width - 3)

    @pytest.mark.parametrize("width", range(3, 12))
    def test_never_parts_a_base_from_its_marks(self, width: int) -> None:
        for text in (SELECTORS, THAI, HINDI, "\U0001f44b\U0001f3fd\U0001f44b\U0001f3fd wave"):
            cell = truncate(text, width)
            if cell == text:
                continue
            kept = cell.removesuffix("...")

            assert text.startswith(kept)
            assert _width(text[len(kept) : len(kept) + 1]) > 0, (text, width, kept)
            assert _width(kept) <= max(0, width - 3)


def test_every_row_starts_the_narration_at_the_same_column(tmp_path: Path) -> None:
    rows = _on_terminal(tmp_path, 120)

    starts = {payee: _width(row[: row.index("lunch")]) for payee, row in rows.items()}
    assert len(set(starts.values())) == 1, starts
    assert all(payee in rows[payee] for payee in PAYEES), rows


def test_a_narrow_terminal_cuts_between_clusters(tmp_path: Path) -> None:
    rows = _on_terminal(tmp_path, 62)

    starts = {payee: _width(row[: row.index("lunch")]) for payee, row in rows.items()}
    assert len(set(starts.values())) == 1, starts
    assert max(_width(row) for row in rows.values()) <= 62, rows
    cut = 0
    for payee, row in rows.items():
        cell = re.split(r" {2,}", row)[2]
        if not cell.endswith("..."):
            assert cell == payee
            continue
        cut += 1
        kept = cell.removesuffix("...")
        assert payee.startswith(kept), (payee, cell)
        assert not kept.endswith(JOINER), (payee, cell)
        assert _width(payee[len(kept) : len(kept) + 1]) > 0, (payee, cell)
    assert cut, rows
