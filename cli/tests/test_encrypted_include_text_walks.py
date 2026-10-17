"""An encrypted include is skipped by `format` and not parsed as text by doctor (w5/495).

Beancount decrypts `.gpg` (and armored `.asc`) includes on load, but
`format` read the ciphertext and advised re-saving it as UTF-8, plaintext
secrets included, and `doctor print-options`/`roundtrip` failed on it as a
syntax error. A fake `gpg` on PATH stands in for the real decryption.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from cli.output import is_encrypted

ROOT = Path(__file__).resolve().parents[1]
PLAIN = '2024-01-05 * "secret"\n  Expenses:Food  10 USD\n  Assets:Cash\n'
LEDGER = 'include "secret.bean.gpg"\n2024-01-01 open Assets:Cash USD\n2024-01-01 open Expenses:Food USD\n'


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "bin").mkdir()
    (tmp_path / "plain.txt").write_text(PLAIN)
    gpg = tmp_path / "bin" / "gpg"
    gpg.write_text(f'#!/bin/sh\ncat "{tmp_path / "plain.txt"}"\n')
    gpg.chmod(0o755)
    (tmp_path / "secret.bean.gpg").write_bytes(b"\x85\x01\x0c\x03\xff\xfe binary ciphertext")
    (tmp_path / "main.bean").write_text(LEDGER)
    return tmp_path


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        PATH=f"{books / 'bin'}{os.pathsep}{os.environ['PATH']}",
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        cwd=books,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_the_fixture_loads(books: Path) -> None:
    result = _bea(books, "-f", "main.bean", "check")
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("flags", [("--check",), ("--dry-run",)])
def test_format_skips_the_encrypted_member(books: Path, flags: tuple[str, ...]) -> None:
    result = _bea(books, "format", *flags, "main.bean")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "secret.bean.gpg: it is encrypted" in result.stderr
    assert "UTF-8" not in result.stdout + result.stderr
    assert (books / "secret.bean.gpg").read_bytes().startswith(b"\x85\x01")


@pytest.mark.parametrize("op", ["print-options", "roundtrip"])
def test_doctor_loads_through_the_encrypted_member(books: Path, op: str) -> None:
    result = _bea(books, "doctor", op, "main.bean")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Invalid token" not in result.stdout + result.stderr


def test_the_rule_matches_upstream(tmp_path: Path) -> None:
    armored = tmp_path / "a.asc"
    armored.write_text("-----BEGIN PGP MESSAGE-----\n\nhQEMA...\n")
    plain = tmp_path / "b.asc"
    plain.write_text("2024-01-01 open Assets:Cash\n")

    assert is_encrypted(tmp_path / "x.bean.gpg")
    assert is_encrypted(armored)
    assert not is_encrypted(plain)
    assert not is_encrypted(tmp_path / "main.bean")
