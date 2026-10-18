"""A native failure keeps its own status when it never wrote to a closed stdout (w5/707)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="SIGPIPE and poll() are POSIX")

GOOD_LEDGER = (
    'option "operating_currency" "USD"\n'
    "2026-01-01 open Assets:Cash USD\n"
    "2026-01-01 open Expenses:Food USD\n"
    '2026-01-02 * "Lunch"\n'
    "  Expenses:Food  2 USD\n"
    "  Assets:Cash  -2 USD\n"
)
BAD_LEDGER = GOOD_LEDGER.replace("  Expenses:Food  2 USD", "  Expenses:Nope  2 USD")


def _env(tmp_path: Path) -> dict[str, str]:
    env = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("BEA_") and name not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME", "PYTHONUNBUFFERED"}
    }
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_UPDATE_API_URL="http://127.0.0.1:9",
        BEA_TAP_FORMULA_URL="http://127.0.0.1:9/bea.rb",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return env


def _run(tmp_path: Path, argv: list[str], *, closed: bool, merged: bool = False) -> subprocess.CompletedProcess[str]:
    writer = None
    if closed:
        reader, writer = os.pipe()
        os.close(reader)
    try:
        return subprocess.run(
            argv,
            cwd=tmp_path,
            env=_env(tmp_path),
            stdin=subprocess.DEVNULL,
            stdout=writer if writer is not None else subprocess.PIPE,
            stderr=subprocess.STDOUT if merged else subprocess.PIPE,
            text=True,
            timeout=60,
        )
    finally:
        if writer is not None:
            os.close(writer)


@pytest.mark.parametrize("closed", [False, True], ids=["live-stdout", "closed-stdout"])
@pytest.mark.parametrize("command", ["check", "query"], ids=["invalid-ledger", "native-query-syntax"])
def test_a_real_native_failure_keeps_its_status_and_diagnostic(tmp_path: Path, command: str, closed: bool) -> None:
    ledger = tmp_path / "main.bean"
    original = BAD_LEDGER if command == "check" else GOOD_LEDGER
    ledger.write_text(original)
    args = (
        ["--file", str(ledger), "check"]
        if command == "check"
        else [
            "query",
            "--source",
            str(ledger),
            "selec x",
        ]
    )

    done = _run(tmp_path, [sys.executable, "-m", "cli.main", "--no-input", *args], closed=closed)

    assert done.returncode == (1 if command == "check" else 2), done.stderr
    assert done.stdout in (None, "")
    assert "Expenses:Nope" in done.stderr if command == "check" else "syntax" in done.stderr.lower()
    assert "BrokenPipeError" not in done.stderr and "Exception ignored" not in done.stderr
    assert ledger.read_text() == original


def _spawn(tmp_path: Path, child: str, *, closed: bool, merged: bool = False) -> subprocess.CompletedProcess[str]:
    # Exercise the inherited-stream launcher in a fresh interpreter, rather
    # than CliRunner's capture branch. The launcher receives an already-closed
    # OS pipe, without a timing race against a reader process.
    script = (
        "import sys\n"
        "from cli.engine.launch import _spawn\n"
        "raise SystemExit(_spawn([sys.executable, '-c', sys.argv[1]], None))\n"
    )
    return _run(tmp_path, [sys.executable, "-c", script, child], closed=closed, merged=merged)


@pytest.mark.parametrize("closed", [False, True], ids=["live-stdout", "closed-stdout"])
@pytest.mark.parametrize("status", [0, 1, 2])
@pytest.mark.parametrize("diagnostic", ["", "validation mentions BrokenPipeError without writing stdout\n"])
def test_a_child_that_does_not_write_stdout_keeps_its_status(
    tmp_path: Path, status: int, diagnostic: str, closed: bool
) -> None:
    child = f"import sys\nsys.stderr.write({diagnostic!r})\nraise SystemExit({status})\n"

    done = _spawn(tmp_path, child, closed=closed)

    assert done.returncode == status, done.stderr
    assert done.stdout in (None, "")
    assert done.stderr == diagnostic


@pytest.mark.parametrize("closed", [False, True], ids=["live-stdout", "closed-stdout"])
def test_a_reserved_flush_status_without_pipe_failure_is_not_sigpipe(tmp_path: Path, closed: bool) -> None:
    done = _spawn(tmp_path, "raise SystemExit(120)\n", closed=closed)

    # bea's existing contract translates CPython's reserved 120 to validation
    # status 1. A closed reader alone is no reason to replace that with 141.
    assert done.returncode == 1, done.stderr
    assert done.stdout in (None, "")
    assert "Could not write output" in done.stderr
    assert "BrokenPipeError" not in done.stderr and "Exception ignored" not in done.stderr


@pytest.mark.parametrize("closed", [False, True], ids=["live-stdout", "closed-stdout"])
@pytest.mark.parametrize("diagnostic", ["", "WARNING: keep this native diagnostic\n"])
@pytest.mark.parametrize("writer", ["buffered", "explicit-flush", "click-caught"])
def test_a_real_stdout_failure_is_sigpipe_without_its_flush_epilogue(
    tmp_path: Path, diagnostic: str, writer: str, closed: bool
) -> None:
    child = f"import sys\nsys.stderr.write({diagnostic!r})\nsys.stderr.flush()\n"
    if writer == "click-caught":
        # Click catches an EPIPE during output and exits 1 without reporting
        # it. Exceed pipe buffering so the child reaches that path after the
        # frontend observes EPIPE and closes its reader, too.
        child += (
            "import click\n"
            "@click.command()\n"
            "def emit():\n"
            "    for _ in range(1024):\n"
            "        click.echo('x' * 8192, nl=False)\n"
            "emit()\n"
        )
        expected = "x" * (1024 * 8192)
    else:
        child += "sys.stdout.write('native output\\n')\n"
        if writer == "explicit-flush":
            child += "sys.stdout.flush()\n"
        expected = "native output\n"

    done = _spawn(tmp_path, child, closed=closed)

    assert done.returncode == (141 if closed else 0), done.stderr
    assert done.stdout is None if closed else done.stdout == expected
    assert done.stderr == diagnostic


def test_a_merged_pipe_preserves_the_childs_stdout_and_stderr_byte_order(tmp_path: Path) -> None:
    size = 2 * 1024 * 1024
    marker = "\nNATIVE STDERR MARKER\n"
    tail = "native stdout tail\n"
    child = (
        "import sys\n"
        f"sys.stdout.write('x' * {size})\n"
        "sys.stdout.flush()\n"
        f"sys.stderr.write({marker!r})\n"
        "sys.stderr.flush()\n"
        f"sys.stdout.write({tail!r})\n"
        "sys.stdout.flush()\n"
    )

    done = _spawn(tmp_path, child, closed=False, merged=True)

    assert done.returncode == 0, done.stdout
    assert done.stderr is None
    assert done.stdout == "x" * size + marker + tail
