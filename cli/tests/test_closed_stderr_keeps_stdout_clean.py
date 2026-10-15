"""With stderr closed (`2>&-`), diagnostics never land in stdout (w5/308).

Python leaves `sys.stderr` None then, and `print(..., file=None)` writes to
stdout: tolerated loader errors opened a `query -f csv` export and trailed a
`--json` envelope, both with exit 0, and error messages became results.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="closes a POSIX descriptor")

ROOT = Path(__file__).resolve().parents[1]
BAD = 'option "operating_currency" "USD"\n2026-01-02 * "x"\n  Assets:Nope  1 USD\n  Equity:Opening\n'
GOOD = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n'


def _bea(tmp_path: Path, *args: str, closed: bool) -> subprocess.CompletedProcess[str]:
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
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        # `2>&-`: the child starts with no descriptor 2 at all.
        preexec_fn=(lambda: os.close(2)) if closed else None,  # noqa: PLW1509 - no threads started yet
        text=True,
        timeout=120,
    )


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "bad.bean").write_text(BAD)
    (tmp_path / "good.bean").write_text(GOOD)
    return tmp_path


@pytest.mark.parametrize("closed", [False, True], ids=["devnull", "closed"])
def test_a_tolerated_csv_export_starts_with_its_header(books: Path, closed: bool) -> None:
    result = _bea(
        books, "-f", "bad.bean", "query", "--allow-errors", "-f", "csv", "SELECT account, number", closed=closed
    )
    assert result.returncode == 0
    assert result.stdout.splitlines()[0] == "account,number"


@pytest.mark.parametrize("closed", [False, True], ids=["devnull", "closed"])
def test_a_tolerated_json_list_is_one_envelope(books: Path, closed: bool) -> None:
    result = _bea(books, "--json", "-f", "bad.bean", "list", "transaction", "--allow-errors", closed=closed)
    assert result.returncode == 0
    json.loads(result.stdout)


@pytest.mark.parametrize(
    ("args", "code"),
    [
        (("--json", "-f", "good.bean", "report", "balance-sheet", "-t", "nonsense"), 2),
        (("-f", "good.bean", "report", "balance-sheet", "-t", "nonsense"), 2),
        (("nosuchcommand",), 2),
        (("-f", "bad.bean", "check"), 1),
    ],
)
def test_a_failure_writes_nothing_to_stdout(books: Path, args: tuple[str, ...], code: int) -> None:
    result = _bea(books, *args, closed=True)
    assert result.returncode == code
    assert result.stdout == ""
