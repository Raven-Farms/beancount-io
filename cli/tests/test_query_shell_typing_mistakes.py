"""A mistyped date and an out-of-range ORDER BY index are explained at the prompt (w5/109).

Both are ordinary typing mistakes, and the one-shot form explains each in a
sentence. At the interactive prompt they printed a Python traceback instead:
the date-literal translation lived only on the one-shot path, and a Beanquery
error that carries no parse position fell through to upstream's renderer,
which formats a stack for anything it cannot point a caret at.

The prompt now says what the one-shot says, on both the `--file` and the
`--source` shell, and `bea --debug` is how to ask for the stack.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from tests.query_terminal import QueryTerminal

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Food USD
2026-01-05 * "Cafe" "Coffee"
  Expenses:Food  4.00 USD
  Assets:Checking
2026-01-06 query "ordered" "SELECT account, sum(position) GROUP BY 1 ORDER BY 3"
"""

BAD_DATE = "SELECT date WHERE date = 2026-02-30"
BAD_ORDER = "SELECT account, sum(position) GROUP BY 1 ORDER BY 3"
DATE_MESSAGE = "Cannot run this BQL query: invalid date literal: day is out of range for month."
DATE_HINT = "Write dates as YYYY-MM-DD with a real month and day, for example 2020-02-29."
ORDER_MESSAGE = "Cannot run this BQL query: invalid ORDER-BY column index 3."
TRACEBACK = "Traceback (most recent call last)"

SHELLS = pytest.mark.parametrize("native", [False, True], ids=["file", "source"])


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(LEDGER, encoding="utf-8")
    return path


def _shell_args(ledger: Path, native: bool) -> list[str]:
    return ["query", "--source", str(ledger)] if native else ["--file", str(ledger), "query"]


@SHELLS
def test_both_mistakes_are_explained_in_the_one_shot_words(tmp_path: Path, ledger: Path, native: bool) -> None:
    with QueryTerminal(tmp_path, _shell_args(ledger, native)) as shell:
        shell.read("beanquery>")

        shell.send(BAD_DATE + ";")
        date_reply = shell.read("beanquery>")
        assert DATE_MESSAGE in date_reply
        assert DATE_HINT in date_reply
        assert "ValueError" not in date_reply

        shell.send(BAD_ORDER + ";")
        order_reply = shell.read("beanquery>")
        assert ORDER_MESSAGE in order_reply
        assert "CompilationError" not in order_reply
        # The terminal may echo the typed line; between it and the next prompt is one line.
        said = [line for line in order_reply.splitlines() if line.strip() and BAD_ORDER not in line]
        assert said == [ORDER_MESSAGE, "beanquery> "]

        shell.send("SELECT count(*) AS n;")
        assert "\n2\n" in shell.read("beanquery>"), "the session keeps answering afterwards"
        assert shell.finish() == 0
        assert TRACEBACK not in shell.screen
    assert ledger.read_text(encoding="utf-8") == LEDGER


@SHELLS
def test_a_stored_query_with_the_same_mistake_is_explained_too(tmp_path: Path, ledger: Path, native: bool) -> None:
    with QueryTerminal(tmp_path, _shell_args(ledger, native)) as shell:
        shell.read("beanquery>")
        shell.send(".run ordered")
        assert ORDER_MESSAGE in shell.read("beanquery>")
        assert shell.finish() == 0
        assert TRACEBACK not in shell.screen


def test_an_error_upstream_can_point_at_keeps_its_caret(tmp_path: Path, ledger: Path) -> None:
    """The control: a Beanquery error with a parse position is still upstream's to render."""
    with QueryTerminal(tmp_path, _shell_args(ledger, False)) as shell:
        shell.read("beanquery>")
        shell.send("SELECT nocol;")
        reply = shell.read("beanquery>")
        assert 'error: column "nocol" not found in table "postings"' in reply
        assert "^^^^^" in reply
        assert shell.finish() == 0
        assert TRACEBACK not in shell.screen


@SHELLS
def test_debug_follows_each_explanation_with_its_traceback(tmp_path: Path, ledger: Path, native: bool) -> None:
    with QueryTerminal(tmp_path, ["--debug", *_shell_args(ledger, native)]) as shell:
        shell.read("beanquery>")

        shell.send(BAD_DATE + ";")
        date_reply = shell.read("beanquery>")
        assert DATE_MESSAGE in date_reply
        assert TRACEBACK in date_reply
        assert "ValueError: day is out of range for month" in date_reply

        shell.send(BAD_ORDER + ";")
        order_reply = shell.read("beanquery>")
        assert ORDER_MESSAGE in order_reply
        assert TRACEBACK in order_reply
        assert "CompilationError: invalid ORDER-BY column index 3" in order_reply

        shell.send("SELECT count(*) AS n;")
        assert TRACEBACK not in shell.read("beanquery>"), "a query that works prints no stack"
        assert shell.finish() == 0


@SHELLS
@pytest.mark.parametrize(
    ("statement", "message"), [(BAD_DATE, DATE_MESSAGE), (BAD_ORDER, ORDER_MESSAGE)], ids=["date", "order-by"]
)
def test_the_one_shot_says_the_same_sentence_and_exits_2(
    tmp_path: Path, ledger: Path, native: bool, statement: str, message: str
) -> None:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        HOME=str(tmp_path / "home"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    done = subprocess.run(
        [str(ROOT / ".venv/bin/bea"), *_shell_args(ledger, native), statement],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )

    assert done.returncode == 2, done.stderr
    assert done.stdout == ""
    assert message in done.stderr
    assert "Traceback" not in done.stderr
