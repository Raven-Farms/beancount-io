"""`format` takes an explicitly named ledger whatever its suffix (w5/499).

`books.ledger` was refused with "Expected a .bean or .beancount file, or a
directory." when named, yet formatted when reached through an include; every
other command and bean-format accept it.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
UNALIGNED = """2024-01-01 open Assets:Cash USD
2024-01-01 open Expenses:Food USD
2024-01-05 * "x"
  Expenses:Food 10 USD
  Assets:Cash
"""


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
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
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize("name", ["books.ledger", "journal.txt", "main.bc"])
@pytest.mark.parametrize("form", ["argument", "--file"])
def test_a_named_ledger_is_checked_whatever_its_suffix(tmp_path: Path, name: str, form: str) -> None:
    (tmp_path / name).write_text(UNALIGNED)
    args = ("format", "--check", name) if form == "argument" else ("--file", name, "format", "--check")

    result = _bea(tmp_path, *args)

    assert result.returncode == 1, result.stdout + result.stderr
    assert f"would format: {tmp_path.resolve() / name}" in result.stdout + result.stderr


def test_a_directory_walk_still_picks_ledgers_by_suffix(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("not a ledger {\n")
    (tmp_path / "main.bean").write_text(UNALIGNED)

    result = _bea(tmp_path, "format", "--check", ".")

    assert "main.bean" in result.stdout + result.stderr
    assert "notes.txt" not in result.stdout + result.stderr


def test_a_named_encrypted_file_is_refused_by_name(tmp_path: Path) -> None:
    (tmp_path / "secret.gpg").write_bytes(b"\x85\x01binary")

    result = _bea(tmp_path, "format", "--check", "secret.gpg")

    assert result.returncode == 2
    assert "secret.gpg: it is encrypted" in result.stderr
