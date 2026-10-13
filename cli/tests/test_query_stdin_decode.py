"""`bea query` holds piped BQL to the UTF-8 rule `format -` applies (w5/155)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """\
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD

2026-01-05 * "Café" "Lunch"
  Expenses:Food  12.00 USD
  Assets:Cash
"""
QUERY = "SELECT date, payee WHERE payee = 'Café'\n"
FILE = ("-f", "main.bean", "query")
SOURCE = ("query", "--source", "main.bean")


def _bea(tmp_path: Path, stdin: bytes, locale: str, *args: str) -> subprocess.CompletedProcess[bytes]:
    (tmp_path / "main.bean").write_text(LEDGER, encoding="utf-8")
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("BEA_", "LC_")) and k not in {"CI", "LANG", "PYTHONIOENCODING", "PYTHONUTF8"}
    }
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        LC_ALL=locale,
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        input=stdin,
        capture_output=True,
        timeout=120,
    )


@pytest.mark.parametrize("locale", ["C", "en_US.UTF-8"])
@pytest.mark.parametrize("args", [FILE, SOURCE], ids=["file", "source"])
def test_latin1_query_is_refused_naming_stdin_and_the_byte(tmp_path: Path, locale: str, args: tuple[str, ...]) -> None:
    result = _bea(tmp_path, QUERY.encode("latin-1"), locale, *args)
    stderr = result.stderr.decode()
    assert result.returncode == 2, stderr
    assert "Cannot decode 'stdin' as UTF-8" in stderr
    assert "at byte 37" in stderr
    assert "codec" not in stderr
    assert result.stdout == b""


def test_json_gets_a_usage_envelope_instead_of_empty_rows(tmp_path: Path) -> None:
    result = _bea(tmp_path, QUERY.encode("latin-1"), "C", "--json", *FILE)
    assert result.returncode == 2
    assert result.stdout == b""
    error = json.loads(result.stderr)["error"]
    assert error["category"] == "usage"
    assert error["message"].startswith("Cannot decode 'stdin' as UTF-8: invalid continuation byte at byte 37.")


@pytest.mark.parametrize("encoding", ["utf-16", "utf-16-le"])
def test_utf16_query_is_a_usage_error_not_an_embedded_null(tmp_path: Path, encoding: str) -> None:
    result = _bea(tmp_path, "SELECT date, payee\n".encode(encoding), "C", *FILE)
    stderr = result.stderr.decode()
    assert result.returncode == 2, stderr
    assert "stdin" in stderr
    assert "UTF-16" in stderr
    assert "embedded null" not in stderr


@pytest.mark.parametrize("bom", [b"", b"\xef\xbb\xbf"], ids=["plain", "bom"])
@pytest.mark.parametrize("args", [FILE, SOURCE], ids=["file", "source"])
def test_utf8_query_runs_with_or_without_a_bom(tmp_path: Path, bom: bytes, args: tuple[str, ...]) -> None:
    result = _bea(tmp_path, bom + QUERY.encode(), "C", *args)
    assert result.returncode == 0, result.stderr.decode()
    assert result.stdout.decode().count("2026-01-05  Café") == 2
