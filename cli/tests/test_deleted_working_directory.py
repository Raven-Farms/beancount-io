"""Commands given absolute paths do not depend on the working directory existing (w5/248).

From a working directory that had been removed, `bea init /abs/dir` created the
ledger, printed its success line, then exited 2 with a bare `[Errno 2]` while
choosing the `Next:` hint. The include walk failed the same way until it
stopped consulting the working directory (w5/071).
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="a working directory in use cannot be removed")


def _bea(tmp_path: Path, *args: str, deleted: bool) -> subprocess.CompletedProcess[str]:
    """Run `bea` from a working directory of its own, removed before the command starts when `deleted`."""
    cwd = tmp_path / "cwd"
    cwd.mkdir(exist_ok=True)

    def enter() -> None:
        os.chdir(cwd)
        if deleted:
            os.rmdir(cwd)

    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        HOME=str(tmp_path / "home"),
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    env.pop("CI", None)
    env.pop("PWD", None)
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        preexec_fn=enter,
    )


def _split_ledger(tmp_path: Path) -> Path:
    main = tmp_path / "split" / "main.bean"
    (main.parent / "inc").mkdir(parents=True)
    main.write_text('include "inc/jan.bean"\n2026-01-01 open Assets:Cash USD\n')
    (main.parent / "inc" / "jan.bean").write_text("2026-01-02 open Expenses:Food USD\n")
    return main


@pytest.mark.parametrize("deleted", [True, False])
def test_init_finishes_with_its_hint(tmp_path: Path, deleted: bool) -> None:
    target = tmp_path / "nb"

    result = _bea(
        tmp_path, "--no-input", "init", str(target), "--currency", "USD", "--date", "2026-01-01", deleted=deleted
    )

    assert result.returncode == 0, result.stderr
    assert "Errno" not in result.stderr
    assert (target / "main.bean").is_file()
    lines = result.stdout.splitlines()
    assert lines[0] == f"Created {target / 'main.bean'} with 14 accounts in USD."
    assert lines[1] == f"Next: cd {shlex.quote(str(target))} && bea check"
    assert lines[-1].startswith("Record purchases with bea add transaction")


def test_init_in_the_working_directory_still_gets_the_bare_hint(tmp_path: Path) -> None:
    """Control: the working-directory ledger is still recognised when the directory exists."""
    result = _bea(
        tmp_path,
        "--no-input",
        "init",
        str(tmp_path / "cwd"),
        "--currency",
        "USD",
        "--date",
        "2026-01-01",
        deleted=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Next: bea check" in result.stdout.splitlines()


@pytest.mark.parametrize("deleted", [True, False])
def test_format_check_walks_includes(tmp_path: Path, deleted: bool) -> None:
    main = _split_ledger(tmp_path)

    result = _bea(tmp_path, "format", "--check", str(main), deleted=deleted)

    assert result.returncode == 0, result.stderr
    assert "Errno" not in result.stderr
    assert result.stdout.splitlines() == [
        f"checked: {main.parent / 'inc' / 'jan.bean'}",
        f"checked: {main}",
        "All 2 file(s) are formatted.",
    ]


@pytest.mark.parametrize("deleted", [True, False])
def test_query_writes_its_output_file(tmp_path: Path, deleted: bool) -> None:
    main = _split_ledger(tmp_path)
    destination = tmp_path / "out.csv"

    result = _bea(
        tmp_path,
        "-f",
        str(main),
        "query",
        "select account from #accounts order by account",
        "-f",
        "csv",
        "-o",
        str(destination),
        deleted=deleted,
    )

    assert result.returncode == 0, result.stderr
    assert "Errno" not in result.stderr
    assert destination.read_text().splitlines() == ["account", "Assets:Cash", "Expenses:Food"]
