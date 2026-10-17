"""BQL regex functions and `JOURNAL` patterns get the w5/429 check (w5/509).

`grep`, `grepn`, `subst` and `findfirst` patterns, and a `JOURNAL` account
pattern, went through unchecked: `[[:alpha:]]` read as a character set with
exit 0, and Python's `FutureWarning` reached stderr with the engine's path.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2024-01-01 open Assets:Cash USD
2024-01-01 open Expenses:Food USD
2024-01-05 * "Pay"
  Expenses:Food 5 USD
  Assets:Cash
"""


def _query(tmp_path: Path, statement: str, *flags: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
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
        [sys.executable, "-m", "cli.main", *flags, "-f", str(tmp_path / "main.bean"), "query", statement],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize(
    ("statement", "says"),
    [
        ("SELECT grep('[[:alpha:]]+', narration) AS g", "[:alpha:] is a POSIX class"),
        ("SELECT narration WHERE grep('[[a]', narration) IS NOT NULL", "Possible nested set at position 1"),
        ("SELECT grepn('[[:digit:]]', narration, 0) AS g", "[:digit:] is a POSIX class"),
        ("SELECT subst('[[:space:]]', '-', narration) AS s", "[:space:] is a POSIX class"),
        ("JOURNAL 'Expenses:[[:alpha:]]+'", "[:alpha:] is a POSIX class"),
        ("SELECT narration WHERE grep(upper('[[a]'), narration) IS NOT NULL", "Possible nested set at position 1"),
    ],
    ids=["grep-posix", "grep-nested", "grepn", "subst", "journal", "computed-pattern"],
)
@pytest.mark.parametrize("flags", [(), ("--json",)], ids=["text", "json"])
def test_a_pattern_read_otherwise_is_refused(tmp_path: Path, statement: str, says: str, flags: tuple[str, ...]) -> None:
    result = _query(tmp_path, statement, *flags)

    assert result.returncode == 2, result.stdout + result.stderr
    assert says in result.stdout + result.stderr
    assert "FutureWarning" not in result.stderr
    assert "warning:" not in result.stderr


def test_a_plain_pattern_still_answers(tmp_path: Path) -> None:
    result = _query(tmp_path, "SELECT grep('P.y', narration) AS g")

    assert result.returncode == 0, result.stderr
    assert result.stdout.rstrip().endswith("Pay")
