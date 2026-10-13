"""`--json format -o /dev/stdout` is refused like `-o -` (w5/157).

Only the literal `-` was recognised as stdout, so the device spellings wrote
the formatted ledger and then the envelope to the same stream, exit 0, and
nothing could parse the result.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = (
    "2026-01-01 open Assets:Cash USD\n"
    "2026-01-01 open Expenses:Food USD\n"
    "\n"
    '2026-01-05 * "Café" "Lunch"\n'
    "  Expenses:Food  12.00 USD\n"
    "  Assets:Cash\n"
)
DEVICES = ["/dev/stdout", "/dev/fd/1"]


def _bea(tmp_path: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[bytes]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        HOME=str(tmp_path / "home"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        input=(stdin or "").encode("utf-8"),
        capture_output=True,
        timeout=120,
    )


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(LEDGER, encoding="utf-8")
    return path


def _refusal(spelling: str) -> str:
    return (
        f"In --json mode, --output {spelling} would mix formatted ledger text into the JSON on stdout. "
        "Name a file with --output FILE, or drop --json to write the text to stdout."
    )


@pytest.mark.parametrize("spelling", ["-", *DEVICES])
@pytest.mark.parametrize("from_stdin", [False, True], ids=["file", "stdin"])
def test_json_format_refuses_every_spelling_of_stdout(
    tmp_path: Path, ledger: Path, spelling: str, from_stdin: bool
) -> None:
    source = [] if from_stdin else [ledger.name]
    done = _bea(tmp_path, "--json", "format", *source, "-o", spelling, stdin=LEDGER if from_stdin else None)

    assert done.returncode == 2, done.stderr
    assert done.stdout == b""
    error = json.loads(done.stderr)["error"]
    assert error["category"] == "usage"
    assert error["message"] == _refusal(spelling)
    assert ledger.read_text(encoding="utf-8") == LEDGER


@pytest.mark.parametrize("spelling", ["-", *DEVICES])
@pytest.mark.parametrize("from_stdin", [False, True], ids=["file", "stdin"])
def test_plain_format_still_writes_text_to_stdout(
    tmp_path: Path, ledger: Path, spelling: str, from_stdin: bool
) -> None:
    source = [] if from_stdin else [ledger.name]
    done = _bea(tmp_path, "format", *source, "-o", spelling, stdin=LEDGER if from_stdin else None)

    assert done.returncode == 0, done.stderr
    assert done.stdout.decode("utf-8") == LEDGER


def test_json_format_to_a_named_file_still_answers_with_the_envelope(tmp_path: Path, ledger: Path) -> None:
    done = _bea(tmp_path, "--json", "format", ledger.name, "-o", "out.bean")

    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["data"]["scanned"] == 1
    assert (tmp_path / "out.bean").read_text(encoding="utf-8") == LEDGER
