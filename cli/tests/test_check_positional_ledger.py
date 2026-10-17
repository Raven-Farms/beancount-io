"""`bea check books.bean` (the `bean-check FILE` habit) is sent to `--file` (w5/500).

The path was ignored: the check fell back to `main.bean`, or failed on
upstream's "unexpected extra argument", and `--json` blamed it as a
bean-check option. None of them named `--file`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = "2024-01-01 open Assets:Cash USD\n"
HINT = "bea check takes the ledger from --file, not as an argument: run bea --file books.bean check."


def _bea(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(cwd / "config"),
        XDG_CACHE_HOME=str(cwd / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize("with_main", [False, True], ids=["no-main-bean", "beside-main-bean"])
@pytest.mark.parametrize("flags", [(), ("--json",)], ids=["text", "json"])
def test_a_positional_ledger_gets_the_file_hint(tmp_path: Path, with_main: bool, flags: tuple[str, ...]) -> None:
    (tmp_path / "books.bean").write_text(LEDGER)
    if with_main:
        (tmp_path / "main.bean").write_text(LEDGER)

    result = _bea(tmp_path, *flags, "check", "books.bean")

    assert result.returncode == 2, result.stdout + result.stderr
    assert HINT in result.stdout + result.stderr


def test_a_cache_filename_value_is_not_a_ledger(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "cache.pickle").write_bytes(b"")

    result = _bea(tmp_path, "check", "--cache-filename", "cache.pickle")

    assert HINT.split(":")[0] not in result.stdout + result.stderr
