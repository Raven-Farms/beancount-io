"""An answer table never drops characters, whatever the width (w5/750).

Rich's Markdown table cut cells with `…` at 80 columns — cents and account
names gone with exit 0 — including the documented `--print > FILE` save,
and piped answers hard-wrapped at 80. `COLUMNS=0` printed nothing at all.
Cells now fold, piped output sizes to its content, and non-positive
`COLUMNS` is ignored like every other bea surface ignores it.
"""

from __future__ import annotations

import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from tests.conftest import StubModel, model_answer
from tests.test_into_glob_create import _env

LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n'
ACCOUNT = "Assets:Investments:Brokerage:Retirement:Roth-IRA:Vanguard-Total-Stock"
HEADERS = ["Account", "Jan", "Feb", "Mar"]
ROW1 = [ACCOUNT, "123,456,789,012.35 USD", "123,456,790,112.35 USD", "123,456,791,212.35 USD"]
ROW2 = ["Expenses:Misc", "-27.17 USD", "-1,027.17 USD", "-2,027.17 USD"]
TABLE = (
    "| " + " | ".join(HEADERS) + " |\n"
    "|---|---|---|---|\n" + "| " + " | ".join(ROW1) + " |\n" + "| " + " | ".join(ROW2) + " |\n"
)
FEB = "123,456,790,112.35"


def _content_chars(shown: str) -> Counter[str]:
    """The answer's characters, without table chrome or padding."""
    return Counter(char for char in shown if char.isalnum() or char in ":.,$-")


EXPECTED = _content_chars(" ".join(HEADERS + ROW1 + ROW2))


def _ask(
    tmp_path: Path, ledger: Path, stub: StubModel, *extra: str, columns: str | None = None
) -> subprocess.CompletedProcess[str]:
    env = _env(tmp_path)
    env.update(BEA_TOKEN="stub-token", BEA_API_URL=stub.url, NO_PROXY="127.0.0.1,localhost")
    if columns is not None:
        env["COLUMNS"] = columns
    else:
        env.pop("COLUMNS", None)
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--file", str(ledger), "ask", "--print", "q", *extra],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_print_to_a_file_keeps_every_digit_and_name(tmp_path: Path, stub_model: StubModel) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")
    stub_model.reply = lambda n: model_answer(TABLE)

    result = _ask(tmp_path, ledger, stub_model)

    assert result.returncode == 0, result.stderr
    assert result.stderr == "", result.stderr
    assert ACCOUNT in result.stdout, result.stdout
    assert FEB in result.stdout, result.stdout
    assert "…" not in result.stdout, result.stdout


def test_columns_zero_prints_the_answer(tmp_path: Path, stub_model: StubModel) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")
    stub_model.reply = lambda n: model_answer("January spending was 12.00 USD.")

    result = _ask(tmp_path, ledger, stub_model, columns="0")

    assert result.returncode == 0, result.stderr
    assert "January spending was 12.00 USD." in result.stdout, (result.stdout, result.stderr)


def test_a_narrow_terminal_folds_instead_of_cutting(
    tmp_path: Path, stub_model: StubModel, ask_on_a_terminal: Any
) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")
    stub_model.reply = lambda n: model_answer(TABLE)

    run = ask_on_a_terminal(["--file", str(ledger), "ask", "--print", "q"], [], env_overrides={"COLUMNS": "40"})

    assert run.status == 0, run.screen
    assert "…" not in run.screen, run.screen
    # Folded rows interleave columns, so contiguity cannot hold; the exact
    # multiset proves every character is there exactly once.
    assert _content_chars(run.screen) == EXPECTED, run.screen


def test_a_session_on_a_narrow_terminal_folds_its_tables(
    tmp_path: Path, stub_model: StubModel, ask_on_a_terminal: Any
) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")
    stub_model.reply = lambda n: model_answer(TABLE)

    run = ask_on_a_terminal(
        ["--file", str(ledger), "ask"],
        ["q", "@ENTER", "@WAIT:❯", "@CTRL_D"],
        env_overrides={"COLUMNS": "40"},
    )

    assert run.status == 0, run.screen
    assert "…" not in run.screen, run.screen
    # The welcome and prompt add their own characters; nothing of the answer
    # may be missing.
    assert not (EXPECTED - _content_chars(run.screen)), run.screen


def test_a_session_with_columns_zero_shows_the_answer(
    tmp_path: Path, stub_model: StubModel, ask_on_a_terminal: Any
) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")
    stub_model.reply = lambda n: model_answer("January spending was 12.00 USD.")

    run = ask_on_a_terminal(
        ["--file", str(ledger), "ask"],
        ["q", "@ENTER", "@WAIT:❯", "@CTRL_D"],
        env_overrides={"COLUMNS": "0"},
    )

    assert run.status == 0, run.screen
    assert "January spending was 12.00 USD." in run.screen, run.screen
