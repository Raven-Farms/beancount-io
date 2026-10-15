"""One file included under two names is loaded once and reported (w5/433).

Beancount spots a repeated include by its path text, so a hard link, a
symbolic link, or another letter case or Unicode form on a volume that
ignores them loaded the file twice: every entry in it counted twice, and
`check` passed.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HEAD = 'option "operating_currency" "USD"\n'
OPENS = "2026-01-01 open Assets:Cash USD\n2026-01-01 open Expenses:Food USD\n"


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
        [sys.executable, "-m", "cli.main", "-f", str(books / "main.bean"), *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def _books(tmp_path: Path, *includes: str) -> Path:
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "x.bean").write_text('2026-01-05 * "x"\n  Expenses:Food 1 USD\n  Assets:Cash\n')
    (tmp_path / "main.bean").write_text(HEAD + "".join(f'include "{name}"\n' for name in includes) + OPENS)
    return tmp_path


def _food(books: Path) -> dict[str, str]:
    result = _bea(books, "--json", "balance", "Food", "--allow-errors")
    assert result.returncode == 0, result.stderr
    balance: dict[str, str] = json.loads(result.stdout)["data"]["expenses"]["children"][0]["balance"]
    return balance


@pytest.mark.skipif(sys.platform == "win32", reason="links")
@pytest.mark.parametrize("link", ["hard", "symbolic"])
def test_a_linked_name_is_loaded_once_and_check_fails(tmp_path: Path, link: str) -> None:
    books = _books(tmp_path, "sub/x.bean", "y.bean")
    if link == "hard":
        os.link(books / "sub" / "x.bean", books / "y.bean")
    else:
        (books / "y.bean").symlink_to(books / "sub" / "x.bean")

    checked = _bea(books, "check")
    assert checked.returncode == 1, checked.stderr
    assert (
        f"main.bean:3: Duplicate include: {books / 'y.bean'} is {books / 'sub' / 'x.bean'} under another name"
    ) in checked.stderr

    read = _bea(books, "balance", "Food")
    assert read.returncode == 1
    assert "Duplicate include" in read.stderr
    assert _food(books) == {"USD": "1"}


def test_another_letter_case_is_loaded_once(tmp_path: Path) -> None:
    probe = tmp_path / "Probe"
    probe.write_text("")
    if not (tmp_path / "probe").exists():
        pytest.skip("needs a case-insensitive volume")
    probe.unlink()
    books = _books(tmp_path, "Sub/X.bean", "SUB/x.bean")

    checked = _bea(books, "check")

    assert checked.returncode == 1, checked.stderr
    assert f"Duplicate include: {books / 'SUB' / 'x.bean'} is {books / 'Sub' / 'X.bean'}" in checked.stderr
    assert _food(books) == {"USD": "1"}


def test_a_single_include_is_unaffected(tmp_path: Path) -> None:
    books = _books(tmp_path, "sub/x.bean")
    assert _bea(books, "check").returncode == 0
    assert _food(books) == {"USD": "1"}
