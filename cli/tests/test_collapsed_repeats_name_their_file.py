"""A collapsed repeat in another included file names that file (w5/146).

A refused write that repeats one problem across included files ended `Same
problem on 2 more lines: 1, 1.` — line numbers of two other files, with nothing
saying which.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

OPENS = "2024-01-01 open Assets:Cash USD\n2024-01-01 open Expenses:Food USD\n"
MONTHS = {"mar": "03", "apr": "04", "may": "05"}


def _transaction(month: str) -> str:
    return f'2024-{month}-10 * "x"\n  Expenses:Food  1 USD\n  Assets:Cash\n'


def _close_food(book: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Close an account three later transactions still post to; the write is refused."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(book / "config"),
        XDG_CACHE_HOME=str(book / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    command = ["--file", "main.bean", *args, "add", "close", "--account", "Expenses:Food", "--date", "2024-03-01"]
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *command],
        cwd=book,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _split_book(tmp_path: Path, first: str = _transaction("03")) -> dict[Path, bytes]:
    (tmp_path / "y").mkdir()
    includes = "".join(f'include "y/{name}.bean"\n' for name in MONTHS)
    (tmp_path / "main.bean").write_text(OPENS + includes)
    for name, month in MONTHS.items():
        (tmp_path / "y" / f"{name}.bean").write_text(first if name == "mar" else _transaction(month))
    return {path: path.read_bytes() for path in sorted(tmp_path.rglob("*.bean"))}


def _detail(result: subprocess.CompletedProcess[str]) -> str:
    assert result.returncode == 1, result.stdout + result.stderr
    details: list[str] = json.loads(result.stderr)["error"]["details"]
    assert len(details) == 1, details
    return details[0]


def test_repeats_in_other_included_files_carry_their_file(tmp_path: Path) -> None:
    before = _split_book(tmp_path)
    detail = _detail(_close_food(tmp_path, "--json"))
    year = tmp_path.resolve() / "y"
    assert detail.startswith(f"{year / 'mar.bean'}:1: Invalid reference to inactive account 'Expenses:Food'")
    assert detail.endswith(f"Same problem on 2 more lines: {year / 'apr.bean'}:1, {year / 'may.bean'}:1.")
    assert {path: path.read_bytes() for path in before} == before


def test_the_text_refusal_names_the_other_files(tmp_path: Path) -> None:
    _split_book(tmp_path)
    result = _close_food(tmp_path)
    assert result.returncode == 1, result.stdout + result.stderr
    flat = "".join(result.stderr.split())
    assert "Sameproblemon2morelines:" in flat
    assert "y/apr.bean:1," in flat and "y/may.bean:1." in flat
    assert "morelines:1,1." not in flat


def test_a_repeat_in_the_named_file_stays_a_bare_line(tmp_path: Path) -> None:
    """Only the occurrences outside the first message's file need a path."""
    _split_book(tmp_path, first=_transaction("03") + "\n" + _transaction("03"))
    detail = _detail(_close_food(tmp_path, "--json"))
    year = tmp_path.resolve() / "y"
    assert detail.startswith(f"{year / 'mar.bean'}:1: ")
    assert detail.endswith(f"Same problem on 3 more lines: 5, {year / 'apr.bean'}:1, {year / 'may.bean'}:1.")


def test_a_single_file_ledger_still_lists_bare_lines(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(OPENS + "\n" + "".join(_transaction(month) for month in MONTHS.values()))
    detail = _detail(_close_food(tmp_path, "--json"))
    assert detail.startswith(f"{tmp_path.resolve() / 'main.bean'}:4: ")
    assert detail.endswith("Same problem on 2 more lines: 7, 10.")
