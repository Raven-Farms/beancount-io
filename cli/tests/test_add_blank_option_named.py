"""A blank `bea add` option is named as the option, not the request field (w5/425).

`add price -c ''` said "Request field 'currency' must be a non-empty
string.", naming a field the user never typed; `add open -c ''` names `-c`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _add(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    (books / "main.bean").write_text('option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n')
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(books / "main.bean"), "add", *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=60,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize(
    ("args", "option"),
    [
        (["price", "--date", "2026-01-05", "-c", "", "--amount", "1 USD"], "-c/--currency"),
        (["commodity", "--date", "2026-01-05", "-c", " "], "-c/--currency"),
        (["note", "--date", "2026-01-05", "-a", "", "-m", "x"], "-a/--account"),
        (["note", "--date", "2026-01-05", "-a", "Assets:Cash", "-m", ""], "-m/--comment"),
        (["event", "--date", "2026-01-05", "--type", "", "--description", "x"], "-t/--type"),
    ],
    ids=["price", "commodity", "note-account", "note-comment", "event-type"],
)
def test_the_blank_option_is_named(tmp_path: Path, args: list[str], option: str) -> None:
    result = _add(tmp_path, *args)
    assert result.returncode == 2, result.stderr
    assert f"Error: {option} must not be empty; give it a value.\n" in result.stderr
    assert "Request field" not in result.stderr
