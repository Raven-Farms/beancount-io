"""A forwarded child's failed shutdown flush stays off stderr on a closed pipe (w5/160).

`bea doctor print-options … | head` exited 141 as documented but with CPython's
own `Exception ignored … BrokenPipeError` on stderr: the child had only buffered
its output, so it met the closed pipe when the interpreter flushed stdout on
the way out, after everything upstream could catch. `USAGE.md` promises the
closed-pipe exit carries no message.

The acceptance cases hand `bea` a pipe whose read end is already closed. Output
this small fits any pipe buffer, so racing a real `head` would pass or fail on
scheduling alone.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from cli.engine import launch

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD

2026-01-05 * "Café" "Lunch"
  Expenses:Food  12.00 USD
  Assets:Cash
"""

EPILOGUE = (
    b"Exception ignored in: <_io.TextIOWrapper name='<stdout>' mode='w' encoding='utf-8'>\n"
    b"BrokenPipeError: [Errno 32] Broken pipe\n"
)

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="SIGPIPE and poll() are POSIX")


def _env(tmp_path: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return env


def _books(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER, encoding="utf-8")
    # A BOM sends `doctor` through the engine helper instead of `bean-doctor`.
    (tmp_path / "bom.bean").write_bytes(b"\xef\xbb\xbf" + LEDGER.encode())


def _bea(tmp_path: Path, *args: str, stdout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=_env(tmp_path),
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        stdout=stdout,
        stderr=subprocess.PIPE,
        text=True,
        timeout=120,
    )


def _into_closed_pipe(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    reader, writer = os.pipe()
    os.close(reader)
    try:
        return _bea(tmp_path, *args, stdout=writer)
    finally:
        os.close(writer)


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(("doctor", "print-options", "main.bean"), id="print-options"),
        pytest.param(("doctor", "list-options"), id="list-options"),
        pytest.param(("doctor", "lex", "main.bean"), id="lex"),
        pytest.param(("doctor", "print-options", "bom.bean"), id="engine-helper"),
        # The control: the frontend's own writer was already silent.
        pytest.param(("--file", "main.bean", "list", "transaction"), id="list"),
    ],
)
def test_closed_reader_exits_141_with_an_empty_stderr(tmp_path: Path, args: tuple[str, ...]) -> None:
    _books(tmp_path)
    done = _into_closed_pipe(tmp_path, *args)
    assert done.returncode == 141, done.stderr
    assert done.stderr == ""


def test_a_live_reader_still_gets_the_childs_stderr_and_status(tmp_path: Path) -> None:
    """The relay must not cost a piped run what upstream wrote to stderr."""
    _books(tmp_path)
    logged = _bea(tmp_path, "doctor", "roundtrip", "main.bean", stdout=subprocess.PIPE)
    assert logged.returncode == 0, logged.stderr
    assert "Entries are the same" in logged.stderr

    printed = _bea(tmp_path, "doctor", "print-options", "main.bean", stdout=subprocess.PIPE)
    assert (printed.returncode, printed.stderr) == (0, "")
    assert "operating_currency" in printed.stdout

    refused = _bea(tmp_path, "doctor", "print-options", "absent.bean", stdout=subprocess.PIPE)
    assert refused.returncode not in (0, 141)
    assert refused.stderr.strip()


def _relayed(pieces: list[bytes], capfd: pytest.CaptureFixture[str]) -> str:
    reader, writer = os.pipe()
    relay = threading.Thread(target=launch._relay_stderr, args=(reader,))
    relay.start()
    for piece in pieces:
        os.write(writer, piece)
    os.close(writer)
    relay.join(timeout=30)
    assert not relay.is_alive()
    return capfd.readouterr().err


def test_relay_drops_only_a_closing_epilogue_on_a_closed_pipe(
    monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(launch, "_downstream_pipe_closed", lambda: True)
    # CPython writes the report in fragments; none of them may slip through.
    fragments = [EPILOGUE[index : index + 7] for index in range(0, len(EPILOGUE), 7)]
    assert _relayed([b"WARNING: kept\n", *fragments], capfd) == "WARNING: kept\n"

    # The same words with something after them are the child's own report.
    assert _relayed([EPILOGUE, b"more\n"], capfd) == EPILOGUE.decode() + "more\n"
    assert _relayed([EPILOGUE, b"Exception"], capfd) == EPILOGUE.decode() + "Exception"
    # Another object's failed finalizer is not the stdout flush.
    other = b"Exception ignored in: <generator object rows at 0x1>\nBrokenPipeError: [Errno 32] Broken pipe\n"
    assert _relayed([other], capfd) == other.decode()
    assert _relayed([b"Proceed? [y/N]: "], capfd) == "Proceed? [y/N]: "


def test_relay_keeps_the_epilogue_when_the_reader_is_alive(
    monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(launch, "_downstream_pipe_closed", lambda: False)
    assert _relayed([EPILOGUE], capfd) == EPILOGUE.decode()
