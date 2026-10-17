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


@pytest.mark.parametrize("closed", [False, True], ids=["devnull", "closed"])
def test_a_native_source_export_holds_only_its_rows(books: Path, closed: bool) -> None:
    """An engine child started without fd 2 wrote its errors into the export (w5/583)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    export = books / "out.csv"
    command = [sys.executable, "-m", "cli.main", "query", "--source", "bad.bean", "-f", "csv", "SELECT account, number"]
    with export.open("w") as stream:
        subprocess.run(
            command,
            env=env,
            cwd=books,
            stdout=stream,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            preexec_fn=(lambda: os.close(2)) if closed else None,  # noqa: PLW1509 - no threads started yet
            timeout=120,
        )

    assert export.read_text().splitlines() == ["account,number", "Assets:Nope, 1", "Equity:Opening,-1"]


def test_the_query_shell_with_stderr_closed_exits_on_dot_exit(books: Path) -> None:
    """Its `input()` raised `lost sys.stderr` in a loop that `.exit` could not end (w5/583)."""
    import pty
    import select
    import time

    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    pid, fd = pty.fork()
    if pid == 0:  # pragma: no cover - replaced by exec in the child
        os.chdir(books)
        os.close(2)
        os.execve(sys.executable, [sys.executable, "-m", "cli.main", "-f", "good.bean", "query"], env)
    emitted = b""
    deadline = time.time() + 60
    typed = False
    try:
        while True:
            ready, _, _ = select.select([fd], [], [], 0.2)
            if ready:
                try:
                    emitted += os.read(fd, 65536)
                except OSError:
                    pass
            if not typed and (b"beanquery>" in emitted or b"> " in emitted):
                os.write(fd, b".exit\r")
                typed = True
            finished, status = os.waitpid(pid, os.WNOHANG)
            if finished:
                break
            if time.time() > deadline:
                os.kill(pid, 9)
                os.waitpid(pid, 0)
                raise AssertionError(f"the shell never exited; it printed {len(emitted)} bytes: {emitted[-300:]!r}")
    finally:
        os.close(fd)

    assert typed, emitted
    assert os.waitstatus_to_exitcode(status) == 0, emitted[-500:]
    assert b"lost sys.stderr" not in emitted
