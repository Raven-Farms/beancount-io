"""A `.reload` that cannot read the ledger closes the session until one can (w5/106).

`do_reload` cleared the session's errors and options and only then called the
loader. When the load raised — the file had become unreadable, or was gone —
the old entries stayed attached beside an empty error list, so the strict
gate passed: the next query answered from the ledger as it was before, and
`.errors` printed `(no errors)`. The `OSError` itself reached upstream's
command loop, which rendered it as a Python traceback.

The load now happens first. A failure is one line, the session refuses typed
and stored queries whatever its read policy — there is no partial answer to
opt into, only a stale one — `.errors` names the failure, and a `.reload` that
succeeds lifts it.

The shell only runs on a terminal, so each case drives a real PTY.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from tests.query_terminal import ROOT, QueryTerminal

PROMPT = "beanquery>"
ROOT_TEXT = """option "operating_currency" "USD"
include "child.bean"
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Food USD
2026-01-05 * "Cafe" "Coffee"
  Expenses:Food  4.00 USD
  Assets:Checking
2026-01-06 query "food" "SELECT sum(position) AS food_total WHERE account = 'Expenses:Food'"
"""
CHILD_TEXT = '2026-01-07 note Assets:Checking "from the include"\n'
QUERY = "SELECT sum(position) AS food_total WHERE account = 'Expenses:Food';"
# A rendered table: the header, then its rule.
TABLE = re.compile(r"food_total\s*\n-{5,}")
REFUSAL = "queries are refused until a .reload succeeds"


def _unreadable(path: Path) -> Callable[[], None]:
    path.chmod(0o000)
    return lambda: path.chmod(0o644)


def _missing(path: Path) -> Callable[[], None]:
    aside = path.with_name(path.name + ".aside")
    path.rename(aside)
    return lambda: aside.rename(path)


CASES = {
    "unreadable-root": ("main.bean", _unreadable),
    "missing-root": ("main.bean", _missing),
    "unreadable-include": ("child.bean", _unreadable),
}


def _step(terminal: QueryTerminal, command: str) -> str:
    terminal.send(command)
    return terminal.read(PROMPT)


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("strict", [True, False], ids=["strict", "lenient"])
def test_a_reload_that_cannot_read_the_ledger_closes_the_session(tmp_path: Path, case: str, strict: bool) -> None:
    name, damage = CASES[case]
    if damage is _unreadable and os.geteuid() == 0:
        pytest.skip("root reads a mode-000 file")
    root = tmp_path / "main.bean"
    root.write_text(ROOT_TEXT, encoding="utf-8")
    (tmp_path / "child.bean").write_text(CHILD_TEXT, encoding="utf-8")
    target = tmp_path / name

    with QueryTerminal(tmp_path, [*(("--strict",) if strict else ()), "--file", str(root), "query"]) as terminal:
        terminal.read(PROMPT)
        assert TABLE.search(_step(terminal, QUERY)), terminal.screen

        restore = damage(target)
        try:
            reloaded = _step(terminal, ".reload")
            typed = _step(terminal, QUERY)
            stored = _step(terminal, ".run food")
            errors = _step(terminal, ".errors")
        finally:
            restore()

        said = [line for line in reloaded.splitlines() if line.strip() not in {"", ".reload"} and PROMPT not in line]
        assert len(said) == 1, reloaded
        assert name in said[0] and REFUSAL in said[0]
        for answer in (typed, stored):
            assert REFUSAL in answer, answer
            assert not TABLE.search(answer), "a failed reload must not answer from the earlier load"
        assert name in errors and "(no errors)" not in errors

        recovered = _step(terminal, ".reload")
        assert REFUSAL not in recovered
        assert TABLE.search(_step(terminal, QUERY)), terminal.screen
        assert TABLE.search(_step(terminal, ".run food")), terminal.screen
        assert "(no errors)" in _step(terminal, ".errors")

        assert terminal.finish() == 0
        assert "Traceback" not in terminal.screen, terminal.screen
    assert root.read_text(encoding="utf-8") == ROOT_TEXT, "querying never writes the ledger"


def test_the_one_shot_refusal_is_unchanged(tmp_path: Path) -> None:
    """The control: a one-shot query on an unreadable ledger was always one line and exit 2."""
    if os.geteuid() == 0:
        pytest.skip("root reads a mode-000 file")
    root = tmp_path / "main.bean"
    root.write_text(ROOT_TEXT, encoding="utf-8")
    (tmp_path / "child.bean").write_text(CHILD_TEXT, encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
    )
    restore = _unreadable(root)
    try:
        done = subprocess.run(
            [sys.executable, "-m", "cli.main", "--file", str(root), "query", "SELECT count(*)"],
            env=env,
            cwd=tmp_path,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=120,
        )
    finally:
        restore()

    assert done.returncode == 2, done.stderr
    assert done.stdout == ""
    assert "is not readable" in done.stderr and "Traceback" not in done.stderr
    assert len(done.stderr.strip().splitlines()) == 1, done.stderr
