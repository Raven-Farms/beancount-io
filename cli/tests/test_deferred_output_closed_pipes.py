"""Deferred warnings, notices and bare help retain their documented pipe statuses (w5/707)."""

from __future__ import annotations

import errno
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from cli import update
from cli.main import app

ROOT = Path(__file__).resolve().parents[1]
CLEAN = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n2026-01-01 open Expenses:Food\n'
BROKEN = CLEAN + '2026-01-02 * "lunch"\n  Expenses:Food 2.50 USD\n  Assets:Cash -5.00 USD\n'
CASES = [
    pytest.param("m.bean", ("list", "transaction", "--allow-errors"), "Transaction does not balance", id="list"),
    pytest.param("m.bean", ("balance", "--allow-errors"), "Transaction does not balance", id="balance"),
    pytest.param(
        "m.bean",
        ("query", "SELECT account, sum(position) GROUP BY account", "--allow-errors"),
        "Transaction does not balance",
        id="query",
    ),
    pytest.param("m.bean", ("report", "balance-sheet", "--allow-errors"), "Transaction does not balance", id="report"),
    # JSON check delegates through a successful typer.Exit, rather than the
    # normal-return path used above. Its captured plugin output is deferred.
    pytest.param("noisy.bean", ("check",), "DEFERRED-PLUGIN-OUTPUT", id="native-exit-plugin-output"),
]
NOTICE_RUNNER = """\
import time
from cli import context, main, update
from cli.commands.upgrade import UV_TOOL
context._stdin_is_a_terminal = lambda: True
update._stderr_is_a_terminal = lambda: True
main.current_channel = lambda: UV_TOOL
update.write_cache(time.time(), "9.9.9")
main.app()
"""

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="requires POSIX closed-reader pipe behavior")


def _books(tmp_path: Path) -> None:
    (tmp_path / "m.bean").write_text(BROKEN)
    (tmp_path / "clean.bean").write_text(CLEAN)
    (tmp_path / "noisy.bean").write_text('option "insert_pythonpath" "TRUE"\nplugin "noisy"\n' + CLEAN)
    (tmp_path / "noisy.py").write_text(
        '__plugins__ = ["noisy"]\n'
        "def noisy(entries, options):\n"
        '    print("DEFERRED-PLUGIN-OUTPUT")\n'
        "    return entries, []\n"
    )


def _env(tmp_path: Path, *, notice: bool) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_") and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_UPDATE_API_URL="http://127.0.0.1:9",
        BEA_TAP_FORMULA_URL="http://127.0.0.1:9/bea.rb",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    if not notice:
        env["BEA_NO_UPDATE_NOTIFIER"] = "1"
    return env


def _run(
    tmp_path: Path,
    args: tuple[str, ...],
    *,
    mode: str,
    notice: bool = False,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, "-c", NOTICE_RUNNER] if notice else [sys.executable, "-m", "cli.main"]
    writer = None
    if mode != "live":
        reader, writer = os.pipe()
        os.close(reader)  # The reader is gone before any output, without a timing race.
    try:
        return subprocess.run(
            [*command, *args],
            cwd=tmp_path,
            env=_env(tmp_path, notice=notice) | (extra_env or {}),
            stdin=subprocess.DEVNULL,
            stdout=writer if mode == "both" else subprocess.PIPE if mode == "live" else subprocess.DEVNULL,
            stderr=subprocess.PIPE if mode == "live" else writer,
            text=True,
            timeout=30,
        )
    finally:
        if writer is not None:
            os.close(writer)


@pytest.mark.parametrize(("ledger", "args", "warning"), CASES)
@pytest.mark.parametrize("mode", ["stderr", "both"])
def test_deferred_json_warnings_use_the_pipe_exit_when_stderr_has_no_reader(
    tmp_path: Path, ledger: str, args: tuple[str, ...], warning: str, mode: str
) -> None:
    _books(tmp_path)

    done = _run(tmp_path, ("--json", "--file", ledger, *args), mode=mode)

    assert done.returncode == 141
    assert (tmp_path / "m.bean").read_text() == BROKEN


@pytest.mark.parametrize(("ledger", "args", "warning"), CASES)
def test_live_readers_still_receive_the_json_envelope_and_deferred_diagnostics(
    tmp_path: Path, ledger: str, args: tuple[str, ...], warning: str
) -> None:
    _books(tmp_path)

    done = _run(tmp_path, ("--json", "--file", ledger, *args), mode="live")

    assert done.returncode == 0, done.stderr
    assert "data" in json.loads(done.stdout)
    assert warning in done.stderr
    assert "Traceback" not in done.stderr and "BrokenPipeError" not in done.stderr


@pytest.mark.parametrize("mode", ["stderr", "both", "live"])
def test_bare_help_keeps_usage_status_even_when_its_reader_is_closed(tmp_path: Path, mode: str) -> None:
    done = _run(tmp_path, (), mode=mode)

    assert done.returncode == 2
    if mode == "live":
        assert done.stdout == ""
        assert "Usage:" in done.stderr and "Beancount.io CLI" in done.stderr
        assert "Traceback" not in done.stderr


@pytest.mark.parametrize("command", [("list", "open"), ("check",)], ids=["normal-return", "native-exit"])
@pytest.mark.parametrize("mode", ["stderr", "live"])
def test_a_cached_update_notice_is_guarded_after_both_success_paths(
    tmp_path: Path, command: tuple[str, ...], mode: str
) -> None:
    _books(tmp_path)

    done = _run(tmp_path, ("--file", "clean.bean", *command), mode=mode, notice=True)

    assert done.returncode == (141 if mode == "stderr" else 0), done.stderr
    if mode == "live":
        assert "9.9.9" in done.stderr and "available" in done.stderr
        assert "Traceback" not in done.stderr


@pytest.mark.parametrize(
    ("args", "code", "extra_env"),
    [
        (("--file", "m.bean", "list", "transaction", "--limit", "0"), 2, {}),
        (("cloud", "status"), 3, {"BEA_TOKEN": "synthetic malformed token", "BEA_API_URL": "http://127.0.0.1:9"}),
    ],
    ids=["usage", "authentication"],
)
def test_an_error_keeps_its_own_status_when_only_its_diagnostic_cannot_be_written(
    tmp_path: Path, args: tuple[str, ...], code: int, extra_env: dict[str, str]
) -> None:
    _books(tmp_path)

    done = _run(tmp_path, args, mode="both", extra_env=extra_env)

    assert done.returncode == code


@pytest.mark.parametrize("command", [("list", "open"), ("check",)], ids=["normal-return", "native-exit"])
@pytest.mark.parametrize("failure", ["EFBIG", "ENOSPC", "EDQUOT", "EIO", "abort", "interrupt"])
def test_deferred_notice_write_failures_and_interrupts_use_the_existing_exit_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: tuple[str, ...], failure: str
) -> None:
    _books(tmp_path)

    def notice() -> None:
        if failure == "abort":
            raise typer.Abort()
        if failure == "interrupt":
            raise KeyboardInterrupt()
        raise OSError(getattr(errno, failure), "synthetic output failure")

    monkeypatch.setattr(update, "print_notice", notice)

    done = CliRunner().invoke(app, ["--file", str(tmp_path / "clean.bean"), *command])

    if failure in {"abort", "interrupt"}:
        assert done.exit_code == 130, done.output
        assert done.stderr == ""
    else:
        assert done.exit_code == 1, done.output
        assert "Could not write output: synthetic output failure" in done.stderr
        assert "Traceback" not in done.stderr
