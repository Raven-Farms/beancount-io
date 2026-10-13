"""Ctrl-C while the query shell loads the ledger never yields a partial ledger (w5/233).

The shell hands Ctrl-C back to Python's default handler so it cancels a line.
That handler raises, and while a ledger is parsing it mostly runs inside one
of Beancount's builder callbacks, where the parser catches the exception,
records it as an error, drops that directive and parses on. The shell then
opened on one transaction fewer, and the load cache kept the damaged result,
so `bea check` failed on the unchanged ledger until a file changed.

The harness makes the timing exact: it wraps the transaction callback so the
engine interrupts itself from inside the parser on the first transaction of
the load that finds the trigger file, and it lowers Beancount's one-second
caching threshold so this small ledger is cached like a large one.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from tests.query_terminal import ROOT, QueryTerminal

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX signal semantics")

HARNESS = textwrap.dedent("""
    import os, sys
    if sys.argv[0] == '-m':
        import signal
        import beanquery.shell
        from beancount import loader
        from beancount.parser import grammar

        beanquery.shell.HISTORY_FILENAME = os.environ['TEST_BQL_HISTORY']
        beanquery.shell.INIT_FILENAME = os.environ['TEST_BQL_INIT']
        loader.PICKLE_CACHE_THRESHOLD = 0.0
        loader.initialize(True)
        original = grammar.Builder.transaction

        def transaction(self, *args):
            trigger = os.environ['TEST_INTERRUPT_TRIGGER']
            if os.path.exists(trigger):
                os.unlink(trigger)
                os.kill(os.getpid(), signal.SIGINT)
            return original(self, *args)

        grammar.Builder.transaction = transaction
""")

LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Food USD
2026-01-05 * "Cafe" "one"
  Expenses:Food  1.00 USD
  Assets:Checking
2026-01-06 * "Cafe" "two"
  Expenses:Food  1.00 USD
  Assets:Checking
2026-01-07 * "Cafe" "three"
  Expenses:Food  1.00 USD
  Assets:Checking
"""
COUNT = "SELECT count(*) AS n, sum(number) AS s WHERE account = 'Expenses:Food'"
COMPLETE = "3  3.00"

SHELLS = pytest.mark.parametrize("native", [False, True], ids=["file", "source"])


class Books:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.ledger = directory / "main.bean"
        self.ledger.write_text(LEDGER, encoding="utf-8")
        self.trigger = directory / "interrupt-next-load"
        harness = directory / "harness"
        harness.mkdir()
        (harness / "sitecustomize.py").write_text(HARNESS)
        self.shell_env = {
            "PYTHONPATH": os.pathsep.join((str(harness), str(ROOT / "src"))),
            "TEST_INTERRUPT_TRIGGER": str(self.trigger),
        }

    def shell(self, native: bool) -> QueryTerminal:
        args = ["query", "--source", str(self.ledger)] if native else ["--file", str(self.ledger), "query"]
        return QueryTerminal(self.directory, args, env=self.shell_env)

    def run(self, *args: str) -> subprocess.CompletedProcess[str]:
        """A fresh `bea` on the same cache home, with no harness: what the user runs next."""
        env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
        env.update(
            BEA_CONFIG_DIR=str(self.directory / "config"),
            BEA_ENGINE_DIR=str(self.directory / "engine"),
            BEA_NO_UPDATE_NOTIFIER="1",
            XDG_CACHE_HOME=str(self.directory / "cache"),
            XDG_DATA_HOME=str(self.directory / "data"),
            PYTHONPATH=str(ROOT / "src"),
            NO_COLOR="1",
            CI="",
        )
        return subprocess.run(
            [str(ROOT / ".venv/bin/bea"), "--file", str(self.ledger), *args],
            cwd=self.directory,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            stdin=subprocess.DEVNULL,
        )

    def caches(self) -> list[Path]:
        return [path for path in self.directory.rglob("*") if path.is_file() and "picklecache" in path.name]

    def assert_sound(self) -> None:
        """Later commands, which trust the load cache, see the whole valid ledger."""
        check = self.run("check")
        assert check.returncode == 0, check.stdout + check.stderr
        count = self.run("query", COUNT)
        assert count.returncode == 0, count.stdout + count.stderr
        assert COMPLETE in count.stdout
        assert "KeyboardInterrupt" not in check.stdout + check.stderr + count.stdout + count.stderr
        assert self.ledger.read_text(encoding="utf-8") == LEDGER


@SHELLS
def test_ctrl_c_during_the_startup_load_cancels_the_session(tmp_path: Path, native: bool) -> None:
    books = Books(tmp_path)
    books.trigger.touch()

    with books.shell(native) as shell:
        screen = shell.read(timeout=30)
        status = shell.process.wait(timeout=30)

    assert not books.trigger.exists(), "the interrupt was delivered inside the parser"
    assert status == 130, screen
    assert "beanquery>" not in screen, "no prompt opens on a load that was cancelled"
    assert "KeyboardInterrupt" not in screen
    books.assert_sound()


@SHELLS
def test_ctrl_c_during_a_reload_returns_to_a_prompt_with_complete_data(tmp_path: Path, native: bool) -> None:
    books = Books(tmp_path)

    with books.shell(native) as shell:
        shell.read("beanquery>")
        shell.send(COUNT + ";")
        assert COMPLETE in shell.read("beanquery>"), "the control: an undisturbed load answers in full"
        assert books.caches(), "the harness makes even this small load cached"

        # A changed file, so the reload parses rather than reading the cache.
        books.ledger.write_text(LEDGER + "\n", encoding="utf-8")
        books.trigger.touch()
        shell.send(".reload")
        reply = shell.read("beanquery>")
        assert not books.trigger.exists(), "the interrupt was delivered inside the parser"
        assert "(interrupted)" in reply
        assert "KeyboardInterrupt" not in reply

        shell.send(COUNT + ";")
        assert COMPLETE in shell.read("beanquery>")
        assert shell.finish() == 0
        assert "KeyboardInterrupt" not in shell.screen

    books.ledger.write_text(LEDGER, encoding="utf-8")
    books.assert_sound()
