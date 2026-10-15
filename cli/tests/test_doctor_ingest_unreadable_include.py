"""`doctor` and `ingest extract -e` refuse an unreadable include in one line (w5/438).

w5/120 made an include that is a directory, or that cannot be read, a
one-line exit 2 on every read. `doctor` forwarded to native `bean-doctor`
and Beangulp loaded `-e` itself: both passed Beancount's traceback through.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def _books(tmp_path: Path) -> Path:
    (tmp_path / "inc.bean").mkdir()
    main = tmp_path / "main.bean"
    main.write_text('option "operating_currency" "USD"\ninclude "inc.bean"\n2026-01-01 open Assets:Cash USD\n')
    return main


def _refusal(main: Path) -> str:
    return (
        f"Error: Included file '{main.parent / 'inc.bean'}' (included from '{main}') is not readable: "
        "it is a directory, not a file."
    )


@pytest.mark.parametrize(
    "op", [["print-options"], ["roundtrip"], ["missing-open"], ["context", "3"], ["region", "1:3"]]
)
def test_doctor_names_the_include_in_one_line(tmp_path: Path, op: list[str]) -> None:
    main = _books(tmp_path)

    result = _bea(tmp_path, "doctor", op[0], str(main), *op[1:])

    assert result.returncode == 2, result.stderr
    assert result.stderr.startswith(_refusal(main))
    assert result.stderr.count("\n") == 1
    assert "Traceback" not in result.stdout + result.stderr


def test_ingest_extract_names_the_existing_ledgers_include(tmp_path: Path) -> None:
    main = _books(tmp_path)
    script = tmp_path / "ingest.py"
    script.write_text(textwrap.dedent("from beangulp import Ingest\nif __name__ == '__main__':\n    Ingest([])()\n"))
    (tmp_path / "downloads").mkdir()

    result = runner.invoke(
        app, ["ingest", "extract", "--config", str(script), "-e", str(main), str(tmp_path / "downloads")]
    )

    assert result.exit_code == 2, result.output
    assert _refusal(main) in result.output
    assert "Traceback" not in result.output
