"""`./-` names the file called `-`; only a bare `-` reads stdin (w5/736).

Typer handed the commands a `Path`, and `Path("./-")` normalizes to
`Path("-")`, so the stdin checks compared the normalized value: `add
transactions --from ./-` wrote stdin's rows at exit 0 without ever reading
the file, `format ./-` printed stdin's ledger, and `format -i ./-` refused
as stdin. The stdin decision now reads the raw argument string.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "title" "T"
2026-01-01 open Expenses:Food USD
2026-01-01 open Assets:Cash USD
"""


def _bea(tmp_path: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        input=stdin,
    )


def _rows(narration: str) -> str:
    return (
        '[{"date":"2026-03-01","narration":"'
        + narration
        + '","postings":[{"account":"Expenses:Food","amount":"1 USD"},'
        '{"account":"Assets:Cash","amount":"-1 USD"}]}]'
    )


def test_add_from_dotdash_reads_the_file_named_dash(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "-").write_text(_rows("FROM FILE"))
    result = _bea(
        tmp_path,
        "-f",
        "main.bean",
        "add",
        "transactions",
        "--from",
        "./-",
        stdin=_rows("FROM STDIN"),
    )
    assert result.returncode == 0, result.stderr
    ledger = (tmp_path / "main.bean").read_text()
    assert "FROM FILE" in ledger
    assert "FROM STDIN" not in ledger


def test_format_dotdash_prints_the_file_named_dash(tmp_path: Path) -> None:
    (tmp_path / "-").write_text(LEDGER)
    result = _bea(tmp_path, "format", "./-", stdin="2026-01-01 open Expenses:Other USD\n")
    assert result.returncode == 0, result.stderr
    assert "Expenses:Food" in result.stdout
    assert "Expenses:Other" not in result.stdout


def test_format_in_place_dotdash_targets_the_file(tmp_path: Path) -> None:
    (tmp_path / "-").write_text(LEDGER)
    result = _bea(tmp_path, "format", "-i", "./-")
    assert result.returncode == 0, result.stderr
    assert "1 file(s)" in result.stdout + result.stderr


def test_bare_dash_still_reads_stdin(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "-").write_text(_rows("FROM FILE"))
    added = _bea(tmp_path, "-f", "main.bean", "add", "transactions", "--from", "-", stdin=_rows("FROM STDIN"))
    assert added.returncode == 0, added.stderr
    ledger = (tmp_path / "main.bean").read_text()
    assert "FROM STDIN" in ledger
    assert "FROM FILE" not in ledger
    formatted = _bea(tmp_path, "format", "-", stdin=LEDGER)
    assert formatted.returncode == 0, formatted.stderr
    assert "Expenses:Food" in formatted.stdout
