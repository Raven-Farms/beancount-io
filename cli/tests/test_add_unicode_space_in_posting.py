"""A Unicode space between account and amount is refused, naming it (w5/490).

Beancount's lexer reads a no-break space inside the account token, so
`Expenses:Food\\u00a05 USD` named an account `Expenses:Food\\u00a05`; the
refusal printed it as a plain space and offered an `add open` that created it.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Expenses:Food USD\n2026-01-01 open Assets:Cash USD\n'


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize(
    ("space", "name"),
    [(" ", "U+00A0 (No-Break Space)"), (" ", "U+2009 (Thin Space)"), ("　", "U+3000 (Ideographic Space)")],
)
@pytest.mark.parametrize("other", ["Assets:Cash -5 USD", "Assets:Cash"])
def test_a_unicode_space_in_a_posting_is_refused(tmp_path: Path, space: str, name: str, other: str) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)

    result = _bea(
        tmp_path, "add", "transaction", "X", "--date", "2026-01-05", "-p", f"Expenses:Food{space}5 USD", "-p", other
    )

    assert result.returncode == 2, result.stdout + result.stderr
    assert f"--posting 1 holds {name} at character 14" in result.stderr
    assert "add open" not in result.stderr
    assert (tmp_path / "main.bean").read_text() == LEDGER


def test_a_quoted_label_may_hold_one(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER + "2026-01-01 open Assets:Broker\n")

    result = _bea(
        tmp_path, "add", "transaction", "X", "--date", "2026-01-05",
        "-p", 'Assets:Broker 1 HOOL {5 USD, "lot one"}', "-p", "Assets:Cash",
    )  # fmt: skip

    assert result.returncode == 0, result.stderr


def test_add_open_refuses_an_invisible_character(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)

    result = _bea(tmp_path, "add", "open", "--date", "2026-01-01", "--account", "Expenses:Food 5")

    assert result.returncode == 2, result.stdout + result.stderr
    assert "The character U+00A0 (NO-BREAK SPACE) is not allowed." in result.stderr
    assert (tmp_path / "main.bean").read_text() == LEDGER
