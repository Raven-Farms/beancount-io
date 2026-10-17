"""`format` reports a mode-000 include as unreadable and formats the rest (w5/523).

w5/442 did this for a directory or a broken link; a permission-denied
include still aborted the whole run with "Could not read …", formatting
nothing and carrying no `result`.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAIN = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Equity:Opening
2026-01-02 * "t"
  Assets:Cash   5 USD
  Equity:Opening   -5 USD
include "sub.bean"
"""

pytestmark = pytest.mark.skipif(os.geteuid() == 0, reason="root reads a mode-000 file")


@pytest.fixture
def books(tmp_path: Path) -> Iterator[Path]:
    (tmp_path / "A").mkdir()
    (tmp_path / "A" / "main.bean").write_text(MAIN)
    sub = tmp_path / "A" / "sub.bean"
    sub.write_text('2026-01-03 * "s"\n  Assets:Cash 1 USD\n  Equity:Opening\n')
    sub.chmod(0)
    try:
        yield tmp_path
    finally:
        sub.chmod(0o644)


def _format(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
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


def test_check_names_the_unreadable_include(books: Path) -> None:
    result = _format(books, "format", "--check", "A/main.bean")

    assert result.returncode == 1, result.stdout + result.stderr
    text = result.stdout + result.stderr
    assert 'unreadable include: "sub.bean"' in text and "cannot be read: Permission denied" in text
    assert "would format:" in text and "main.bean" in text
    assert "Could not read" not in text


def test_in_place_formats_the_root_and_reports_the_include(books: Path) -> None:
    before = hashlib.sha256((books / "A" / "main.bean").read_bytes()).hexdigest()

    result = _format(books, "--json", "format", "-i", "A/main.bean")

    assert result.returncode == 1, result.stdout + result.stderr
    error = json.loads(result.stdout or result.stderr)["error"]
    assert [item["include"] for item in error["result"]["missing"]] == ["sub.bean"]
    assert "Permission denied" in error["result"]["missing"][0]["reason"]
    assert hashlib.sha256((books / "A" / "main.bean").read_bytes()).hexdigest() != before
