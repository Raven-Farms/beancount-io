"""Bidirectional override characters are terminal control too (w5/148).

The sanitizer escaped ESC and the rest of C0/C1 so imported text "cannot drive
your terminal", but U+202E (right-to-left override) passed through raw,
directly ahead of the amount cell in the import preview: on a bidi-aware
terminal that reorders how the rest of the row reads, with no ESC byte
involved. `--apply` stored it, and every later `list` printed it again. The
row was also padded one column short, because a format character was counted
as a column it never occupies.

Right-to-left *text* is the control: Hebrew and Arabic letters carry their
direction themselves and must come through untouched.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from bea_engine.ledger.text import refuse_control_characters
from bea_engine.ledger.text import single_line as engine_single_line
from bea_engine.protocol import UsageError as EngineUsageError
from cli.output import display_width
from cli.utils import inert_text
from cli.utils import single_line as frontend_single_line

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Uncategorized USD
"""

RLO = "\u202e"
HEBREW_AND_ARABIC = "\u05e9\u05dc\u05d5\u05dd \u0645\u0631\u062d\u0628\u0627"
ESCAPED_CODE_POINTS = [*range(0x202A, 0x202F), *range(0x2066, 0x206A)]
SANITIZERS = pytest.mark.parametrize(
    "sanitize",
    [frontend_single_line, engine_single_line, inert_text],
    ids=["frontend", "engine", "multi-line"],
)


class TestSanitizer:
    @SANITIZERS
    @pytest.mark.parametrize("code", ESCAPED_CODE_POINTS, ids=lambda code: f"U+{code:04X}")
    def test_every_bidi_control_becomes_a_visible_escape(self, sanitize, code: int) -> None:
        assert sanitize(f"Refund {chr(code)}12.34") == f"Refund \\u{code:04x}12.34"

    @SANITIZERS
    @pytest.mark.parametrize("text", [HEBREW_AND_ARABIC, "日本語 café", "Ünïcödé", "zero\u200bwidth"])
    def test_ordinary_text_in_any_script_is_untouched(self, sanitize, text: str) -> None:
        assert sanitize(text) == text

    @SANITIZERS
    @pytest.mark.parametrize("separator", ["\u2028", "\u2029"], ids=["U+2028", "U+2029"])
    def test_line_and_paragraph_separators_stay_string_content(self, sanitize, separator: str) -> None:
        """A write keeps them byte for byte (w1/136), so the preview must not show otherwise."""
        assert sanitize(f"first{separator}second") == f"first{separator}second"

    def test_latin_1_controls_keep_their_two_digit_form(self) -> None:
        assert frontend_single_line("a\x1bb\x9bc") == engine_single_line("a\x1bb\x9bc") == "a\\x1bb\\x9bc"

    def test_raw_directive_text_is_refused_naming_the_code_point(self) -> None:
        with pytest.raises(EngineUsageError) as caught:
            refuse_control_characters(f'2026-01-01 note Assets:Cash "{RLO}"', what="the directive text")

        assert "\\u202e at offset 29" in str(caught.value)
        refuse_control_characters(f'2026-01-01 note Assets:Cash "{HEBREW_AND_ARABIC}"', what="the directive text")


class TestDisplayWidth:
    @pytest.mark.parametrize(
        ("text", "columns"),
        [
            pytest.param("zero\u200bwidth", 9, id="zero-width-space"),
            pytest.param("a\u200eb\u200fc", 3, id="directional-marks"),
            pytest.param("a\u200db", 2, id="zero-width-joiner"),
            pytest.param("co\u00adop", 5, id="soft-hyphen-takes-a-cell"),
            pytest.param(HEBREW_AND_ARABIC, 10, id="right-to-left-letters"),
        ],
    )
    def test_format_characters_take_no_column(self, text: str, columns: int) -> None:
        assert display_width(text) == columns


def _bea(tmp_path: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        HOME=str(tmp_path / "home"),
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        PYTHONIOENCODING="utf-8",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", "--file", str(tmp_path / "main.bean"), *argv],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER, encoding="utf-8")
    (tmp_path / "bank.csv").write_text(
        "Date,Amount,Description\n"
        f"2026-02-01,-12.34,Refund {RLO}\n"
        "2026-02-02,-5.00,Esc \x1b[31mred\n"
        f"2026-02-03,-1.00,{HEBREW_AND_ARABIC}\n"
        "2026-02-04,-2.00,zero\u200bwidth\n",
        encoding="utf-8",
    )
    return tmp_path


IMPORT = ("import", "bank.csv", "--csv", "auto", "--account", "Assets:Cash")


def _preview_table(stdout: str) -> list[str]:
    lines = stdout.split("\n")
    start = next(i for i, line in enumerate(lines) if line.startswith("ROW"))
    return lines[start : start + 6]


def test_the_import_preview_shows_the_override_and_stays_aligned(books: Path) -> None:
    preview = _bea(books, *IMPORT)

    assert preview.returncode == 0, preview.stderr
    assert RLO not in preview.stdout, "the raw override reached the terminal"
    rows = _preview_table(preview.stdout)
    assert "Refund \\u202e" in rows[2]
    assert "Esc \\x1b[31mred" in rows[3], "the ESC control: escaped before and after"
    assert HEBREW_AND_ARABIC in rows[4], "right-to-left letters are ordinary text"
    assert "zero\u200bwidth" in rows[5]
    # Every row's amount cell starts in the column the header gives it.
    amount_column = display_width(rows[0][: rows[0].index("SOURCE AMOUNT")])
    for row, amount in zip(rows[2:], ["-12.34 USD", "-5.00 USD", "-1.00 USD", "-2.00 USD"], strict=True):
        assert display_width(row[: row.index(amount)]) == amount_column, row


def test_apply_stores_the_escaped_form_and_list_reads_it_back(books: Path) -> None:
    applied = _bea(books, *IMPORT, "--apply")
    assert applied.returncode == 0, applied.stderr

    written = (books / "main.bean").read_text(encoding="utf-8")
    assert RLO not in written
    assert '"Refund \\\\u202e"' in written, "the escaped form is what is stored"
    assert f'"{HEBREW_AND_ARABIC}"' in written

    listed = _bea(books, "list", "transaction")
    assert listed.returncode == 0, listed.stderr
    assert RLO not in listed.stdout
    assert "Refund \\u202e" in listed.stdout
    assert HEBREW_AND_ARABIC in listed.stdout


def test_an_override_already_in_the_ledger_is_escaped_on_read(books: Path) -> None:
    """Books written before the fix, or by hand, still carry the raw character."""
    ledger = books / "main.bean"
    ledger.write_text(
        LEDGER + f'2026-02-01 * "Refund {RLO}"\n  Assets:Cash  -12.34 USD\n  Expenses:Uncategorized\n',
        encoding="utf-8",
    )

    listed = _bea(books, "list", "transaction")

    assert listed.returncode == 0, listed.stderr
    assert RLO not in listed.stdout
    assert "Refund \\u202e" in listed.stdout
    assert RLO in ledger.read_text(encoding="utf-8"), "reading never rewrites the ledger"
