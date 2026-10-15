"""`format` names an include that is not a file instead of calling it missing (w5/442).

The closure walk counted any include without a regular-file match as
missing, so `include "sub"` naming an existing directory sent users looking
for a file that is there; reads already say "a directory, not a file".
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
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
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=60,
        stdin=subprocess.DEVNULL,
    )


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "sub").mkdir()
    (tmp_path / "main.bean").write_text(
        'option "operating_currency" "USD"\ninclude "sub"\ninclude "absent.bean"\n2026-01-01 open Assets:Cash USD\n'
    )
    return tmp_path


@pytest.mark.parametrize("mode", ["--check", "-i"])
def test_a_directory_include_is_named_and_an_absent_one_stays_missing(books: Path, mode: str) -> None:
    main = books / "main.bean"
    result = _bea(books, "format", mode, str(main))
    assert result.returncode == 1, result.stderr
    assert f'unreadable include: "sub" (included by {main}): {books / "sub"} is a directory, not a file' in (
        result.stderr
    )
    assert f'missing include: "absent.bean" (included by {main})' in result.stderr
    assert 'missing include: "sub"' not in result.stderr
    assert "1 include(s) are missing; 1 include(s) name no readable file." in result.stderr


def test_json_carries_the_reason(books: Path) -> None:
    result = _bea(books, "--json", "format", "--check", str(books / "main.bean"))
    assert result.returncode == 1, result.stderr
    missing = json.loads(result.stderr)["error"]["result"]["missing"]
    assert missing == [
        {"include": "sub", "from": str(books / "main.bean"), "reason": f"{books / 'sub'} is a directory, not a file"},
        {"include": "absent.bean", "from": str(books / "main.bean")},
    ]
