"""The query shell's load-error banner cannot drive the terminal (w5/107).

A lenient interactive session on an invalid ledger says so in one place: the
banner Beancount's `printer.print_errors` writes at startup, on `.reload` and
on `.errors`. That block renders the offending entry verbatim, so a payee
carrying a clear-screen sequence wiped the "does not balance" line it was
printed under — the only sign that the session's answers are partial. Every
other diagnostic escapes such bytes; the shell child owns the terminal, so the
frontend's filter never saw this one.

These need a real terminal: the bytes are read back from the PTY.
"""

from __future__ import annotations

from pathlib import Path

from tests.query_terminal import QueryTerminal

ESC = "\x1b"
PROMPT = "beanquery> "
BALANCE_ERROR = "main.bean:7: Transaction does not balance: (1.00 USD)"

HOSTILE = f"""option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Food USD
2026-01-05 * "Cafe" "Coffee"
  Expenses:Food  4.00 USD
  Assets:Checking
2026-01-06 * "Bank{ESC}[2J{ESC}[1;1HFAKE" "imported row"
  Expenses:Food  9.00 USD
  Assets:Checking  -8.00 USD
"""
PLAIN = HOSTILE.replace(f"{ESC}[2J{ESC}[1;1H", " ")
ESCAPED_PAYEE = '"Bank\\x1b[2J\\x1b[1;1HFAKE" "imported row"'


def _ledger(tmp_path: Path, text: str) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(text, encoding="utf-8")
    return ledger


def _banners(tmp_path: Path, ledger: Path) -> tuple[str, str, str, int]:
    """The terminal's bytes at startup, after `.errors` and after `.reload`."""
    with QueryTerminal(tmp_path, ["-f", str(ledger), "query"]) as terminal:
        startup = terminal.read(PROMPT)
        terminal.send(".errors")
        errors = terminal.read(PROMPT)
        terminal.send(".reload")
        reload = terminal.read(PROMPT)
        status = terminal.finish()
    return startup, errors, reload, status


def test_banner_escapes_control_bytes_at_startup_errors_and_reload(tmp_path: Path) -> None:
    startup, errors, reload, status = _banners(tmp_path, _ledger(tmp_path, HOSTILE))

    assert status == 0
    for moment, screen in (("startup", startup), (".errors", errors), (".reload", reload)):
        assert ESC not in screen, f"{moment} sent a raw escape byte: {screen!r}"
        assert BALANCE_ERROR in screen, f"{moment} lost the balance error: {screen!r}"
        assert ESCAPED_PAYEE in screen, f"{moment} does not show the escaped entry: {screen!r}"


def test_banner_without_control_bytes_is_upstreams_block(tmp_path: Path) -> None:
    startup, errors, reload, status = _banners(tmp_path, _ledger(tmp_path, PLAIN))

    block = (
        f"{BALANCE_ERROR}\n"
        "\n"
        '   2026-01-06 * "Bank FAKE" "imported row"\n'
        "     Expenses:Food     9.00 USD\n"
        "     Assets:Checking  -8.00 USD\n"
    )
    assert status == 0
    for moment, screen in (("startup", startup), (".errors", errors), (".reload", reload)):
        assert block in screen, f"{moment} changed the plain banner: {screen!r}"


def test_print_keeps_the_ledgers_exact_bytes(tmp_path: Path) -> None:
    """`PRINT` is ledger output, not a diagnostic: it stays byte-exact (w4/173)."""
    with QueryTerminal(tmp_path, ["-f", str(_ledger(tmp_path, HOSTILE)), "query"]) as terminal:
        terminal.read(PROMPT)
        terminal.send("PRINT FROM year = 2026 AND day = 6")
        printed = terminal.read(PROMPT)
        assert terminal.finish() == 0

    assert f'"Bank{ESC}[2J{ESC}[1;1HFAKE" "imported row"' in printed


def test_one_shot_error_line_has_no_entry_text(tmp_path: Path) -> None:
    """The note's control: the one-shot diagnostic was already inert."""
    ledger = _ledger(tmp_path, HOSTILE)
    with QueryTerminal(tmp_path, ["-f", str(ledger), "query", "SELECT count(*) AS n"]) as terminal:
        screen = terminal.read()

    assert ESC not in screen
    assert "Transaction does not balance: (1.00 USD)" in screen
    assert "FAKE" not in screen
