"""Init and portable exports report writes whose answers or late stops race them (w5/676)."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n'
COMMIT_HOLD = """import os
import time
from pathlib import Path

def after_commit(target):
    if Path(target).absolute() == Path(os.environ["TEST_COMMIT_TARGET"]):
        Path(os.environ["TEST_COMMIT_MARKER"]).write_text("committed\\n")
        time.sleep(0.7)

replace = os.replace
link = os.link
def held_replace(source, target, *args, **kwargs):
    replace(source, target, *args, **kwargs)
    after_commit(target)
def held_link(source, target, *args, **kwargs):
    link(source, target, *args, **kwargs)
    after_commit(target)
os.replace = held_replace
os.link = held_link
"""
HANDOFF_STOP = """import os
import signal
import sys
from pathlib import Path

if "cli.main" in sys.orig_argv:
    from cli.engine import launch
    answered_success = launch._answered_success
    def stop_at_answer(completed):
        marker = Path(os.environ["TEST_HANDOFF_MARKER"])
        if not marker.exists():
            marker.write_text("answer observed\\n")
            os.kill(os.getpid(), signal.SIGTERM)
        return answered_success(completed)
    launch._answered_success = stop_at_answer
"""

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX signals")


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "source").mkdir()
    (tmp_path / "source/main.bean").write_text(LEDGER)
    return tmp_path


def _env(directory: Path, *, override: Path | None = None, shim: Path | None = None) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_") and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    env.update(
        BEA_CONFIG_DIR=str(directory / "config"),
        BEA_ENGINE_DIR=str(directory / "engine"),
        BEA_NO_UPDATE_NOTIFIER="1",
        XDG_CACHE_HOME=str(directory / "cache"),
        XDG_DATA_HOME=str(directory / "data"),
        PYTHONPATH=os.pathsep.join([str(ROOT / "src"), *([str(shim)] if shim else [])]),
        TERM="dumb",
        NO_COLOR="1",
    )
    if override is not None:
        env["BEA_ENGINE_PYTHON"] = str(override)
    return env


def _command(directory: Path, operation: str, structured: bool) -> list[str]:
    args = [sys.executable, "-m", "cli.main", "--no-input", *(["--json"] if structured else [])]
    if operation == "init":
        return [*args, "init", str(directory / "new-books"), "--currency", "USD", "--date", "2026-01-01"]
    return [*args, "--file", str(directory / "source/main.bean"), "price", "export", "-o", str(directory / "export")]


def _target(directory: Path, operation: str) -> Path:
    return directory / ("new-books/main.bean" if operation == "init" else "export/main.bean")


def _assert_written(directory: Path, operation: str) -> None:
    assert (directory / "source/main.bean").read_text() == LEDGER
    target = _target(directory, operation)
    assert target.is_file()
    if operation == "init":
        assert 'option "operating_currency" "USD"' in target.read_text()
        assert "Assets:Checking" in target.read_text()
    else:
        assert target.read_text() == LEDGER


def _wrapper(directory: Path, discard: bool, *, status: int | None = None) -> Path:
    wrapper = directory / "engine-wrapper"
    finish = "os.kill(os.getpid(), signal.SIGKILL)\n" if status is None else f"raise SystemExit({status})\n"
    wrapper.write_text(
        f"#!{sys.executable}\n"
        "import os, signal, subprocess, sys\n"
        f"python = {sys.executable!r}\n"
        "args = sys.argv[1:]\n"
        "if args[:2] == ['-P', '-c']:\n"
        "    os.execv(python, [python, *args])\n"
        f"result = subprocess.run([python, *args], stdout={'subprocess.DEVNULL' if discard else 'None'})\n"
        "if result.returncode:\n"
        "    raise SystemExit(result.returncode)\n" + finish
    )
    wrapper.chmod(0o755)
    return wrapper


@pytest.mark.parametrize("operation", ["init", "export"])
@pytest.mark.parametrize("structured", [False, True], ids=["text", "json"])
def test_a_lost_answer_after_the_write_reports_an_unknown_outcome(
    books: Path, operation: str, structured: bool
) -> None:
    result = subprocess.run(
        _command(books, operation, structured),
        cwd=books,
        env=_env(books, override=_wrapper(books, discard=True)),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 4, result.stdout + result.stderr
    assert result.stdout == ""
    if structured:
        error = json.loads(result.stderr)["error"]
        assert (error["category"], error["exit_code"]) == ("conflict", 4)
        message = error["message"]
    else:
        message = result.stderr
    assert "SIGKILL" in message
    assert "outcome is unknown" in message
    assert "Inspect the file before retrying" in message
    _assert_written(books, operation)


@pytest.mark.parametrize("operation", ["init", "export"])
@pytest.mark.parametrize("structured", [False, True], ids=["text", "json"])
def test_a_retained_success_answer_still_reports_success_when_the_wrapper_dies(
    books: Path, operation: str, structured: bool
) -> None:
    result = subprocess.run(
        _command(books, operation, structured),
        cwd=books,
        env=_env(books, override=_wrapper(books, discard=False)),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout
    assert "outcome is unknown" not in result.stderr
    if structured:
        assert json.loads(result.stdout)["data"]
    _assert_written(books, operation)


@pytest.mark.parametrize("operation", ["init", "export"])
@pytest.mark.parametrize("stop", [signal.SIGTERM, signal.SIGINT, signal.SIGHUP], ids=["SIGTERM", "SIGINT", "SIGHUP"])
def test_a_frontend_stop_after_commit_keeps_the_reported_success(
    books: Path, operation: str, stop: signal.Signals
) -> None:
    shim = books / "shim"
    shim.mkdir()
    (shim / "sitecustomize.py").write_text(COMMIT_HOLD)
    marker = books / "committed.marker"
    env = _env(books, shim=shim)
    env.update(TEST_COMMIT_TARGET=str(_target(books, operation)), TEST_COMMIT_MARKER=str(marker))
    process = subprocess.Popen(
        _command(books, operation, structured=False),
        cwd=books,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 30
        while not marker.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert marker.exists(), process.communicate(timeout=10)
        process.send_signal(stop)
        out, err = process.communicate(timeout=15)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)

    assert process.returncode == 0, (process.returncode, out, err)
    assert ("Created" if operation == "init" else "Exported") in out
    assert f"Stopped ({stop.name}) after the write had completed; its result stands" in err
    _assert_written(books, operation)


@pytest.mark.parametrize("operation", ["init", "export"])
def test_healthy_init_and_export_still_report_their_files(books: Path, operation: str) -> None:
    result = subprocess.run(
        _command(books, operation, structured=True),
        cwd=books,
        env=_env(books),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["data"]
    _assert_written(books, operation)


@pytest.mark.parametrize("operation", ["status", "refresh"])
def test_price_reads_keep_validation_failure_for_a_missing_answer(books: Path, operation: str) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cli.main",
            "--no-input",
            "--json",
            "--file",
            str(books / "source/main.bean"),
            "price",
            operation,
        ],
        cwd=books,
        env=_env(books, override=_wrapper(books, discard=True)),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stdout == ""
    error = json.loads(result.stderr)["error"]
    assert (error["category"], error["exit_code"]) == ("validation", 1)
    assert "SIGKILL" in error["message"]
    assert "produced no result" in error["message"]
    assert "outcome is unknown" not in result.stderr
    assert (books / "source/main.bean").read_text() == LEDGER
    assert not (books / "export").exists()
    assert not (books / "new-books").exists()


@pytest.mark.parametrize("operation", ["init", "export"])
def test_a_plain_nonzero_exit_after_the_write_also_has_an_unknown_outcome(books: Path, operation: str) -> None:
    result = subprocess.run(
        _command(books, operation, structured=True),
        cwd=books,
        env=_env(books, override=_wrapper(books, discard=True, status=9)),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 4, result.stdout + result.stderr
    assert result.stdout == ""
    error = json.loads(result.stderr)["error"]
    assert (error["category"], error["exit_code"]) == ("conflict", 4)
    assert "exit 9" in error["message"]
    assert "outcome is unknown" in error["message"]
    _assert_written(books, operation)


def test_a_stop_during_answer_handoff_never_restores_default_handlers_over_a_commit(books: Path) -> None:
    shim = books / "shim"
    shim.mkdir()
    (shim / "sitecustomize.py").write_text(HANDOFF_STOP)
    marker = books / "handoff.marker"
    env = _env(books, shim=shim)
    env["TEST_HANDOFF_MARKER"] = str(marker)

    result = subprocess.run(
        _command(books, "init", structured=False),
        cwd=books,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert marker.exists(), result.stdout + result.stderr
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    assert "Created" in result.stdout
    assert "Stopped (SIGTERM) after the write had completed; its result stands" in result.stderr
    _assert_written(books, "init")
