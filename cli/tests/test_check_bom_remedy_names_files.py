"""The BOM remedy `bea check` prints is a command that runs (w5/197).

It said "Run bea format -i to strip the mark", but bare `bea format -i` reads
stdin and is refused, so a ledger found through the current directory or
`BEA_FILE` kept its mark and the original command failed again.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BOM = b"\xef\xbb\xbf"


def _bea(tmp_path: Path, cwd: Path, *args: str, **extra: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in {"BEA_FILE", "BEA_TOKEN", "CI"}}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
        **extra,
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=120,
    )


@pytest.mark.parametrize("source", ["cwd", "BEA_FILE"])
def test_the_printed_remedy_strips_the_mark_and_check_proceeds(tmp_path: Path, source: str) -> None:
    books = tmp_path / "my books"
    books.mkdir()
    main, marked, plain = books / "main.bean", books / "marked.bean", books / "plain.bean"
    main.write_bytes(BOM + b'include "marked.bean"\ninclude "plain.bean"\n2020-01-01 open Assets:Cash USD\n')
    marked.write_bytes(BOM + b"2020-01-01 open Assets:Bank USD\n")
    plain.write_bytes(b"2020-01-01 open Assets:Card USD\n")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    cwd, extra = (books, {}) if source == "cwd" else (elsewhere, {"BEA_FILE": str(main)})

    refused = _bea(tmp_path, cwd, "check", "--auto", **extra)

    assert refused.returncode == 2, refused.stderr
    assert "cannot pass bean-check options (--auto)" in refused.stderr
    command = refused.stderr.split("Run ", 1)[1].split(" to strip the mark, then retry.", 1)[0]
    argv = shlex.split(command)
    assert argv[:3] == ["bea", "format", "-i"]
    assert {Path(name).resolve() for name in argv[3:]} == {main.resolve(), marked.resolve()}

    # Control: the bare command the message used to print is still refused.
    bare = _bea(tmp_path, cwd, "format", "-i", **extra)
    assert bare.returncode == 2, bare.stderr
    assert main.read_bytes().startswith(BOM)

    # The printed command, run from an unrelated directory, clears every marked file.
    fixed = _bea(tmp_path, elsewhere, *argv[1:])

    assert fixed.returncode == 0, fixed.stderr
    assert not main.read_bytes().startswith(BOM)
    assert not marked.read_bytes().startswith(BOM)
    retried = _bea(tmp_path, cwd, "check", "--auto", **extra)
    assert retried.returncode == 0, retried.stderr
