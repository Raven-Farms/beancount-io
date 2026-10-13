"""With `BEA_FILE` set, the next steps init prints must still act on the ledger it created (w5/114)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# A ledger that fails `bea check`: if a hint lands here, it exits 1.
OTHER_LEDGER = """\
2024-01-01 open Assets:Checking USD
2024-01-01 open Expenses:Groceries USD
2024-01-05 * "bad"
  Expenses:Nope  1 USD
  Assets:Checking
"""

pytestmark = pytest.mark.skipif(
    sys.platform == "win32" or not Path("/bin/sh").exists(), reason="executes the hint in a POSIX shell"
)


def _env(home: Path, bea_file: str | None) -> dict[str, str]:
    """An isolated environment whose home is `home` and whose PATH resolves `bea` to this checkout."""
    bin_dir = home / ".bin"
    bin_dir.mkdir(exist_ok=True)
    shim = bin_dir / "bea"
    shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" -m cli.main "$@"\n')
    shim.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        HOME=str(home),
        PATH=f"{bin_dir}{os.pathsep}{env.get('PATH', '')}",
        BEA_CONFIG_DIR=str(home / ".config"),
        XDG_CACHE_HOME=str(home / ".cache"),
        XDG_DATA_HOME=str(home / ".data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    if bea_file is not None:
        env["BEA_FILE"] = bea_file
    return env


def _sh(command: str, env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/sh", "-c", command],
        env=env,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _init(env: dict[str, str], cwd: Path, target: str) -> tuple[str, str]:
    """Run init and return its `Next:` command and its `Record purchases …` line."""
    result = subprocess.run(
        ["bea", "init", target, "--currency", "USD", "--date", "2026-08-01"],
        env=env,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    lines = result.stdout.splitlines()
    hints = [line.removeprefix("Next: ") for line in lines if line.startswith("Next: ")]
    records = [line for line in lines if line.startswith("Record purchases with ")]
    assert len(hints) == 1 and len(records) == 1, result.stdout
    return hints[0], records[0]


@pytest.mark.parametrize("target", ["books", ".", "my books/custom.bean"])
def test_next_steps_reach_the_new_ledger_while_bea_file_names_another(tmp_path: Path, target: str) -> None:
    home = tmp_path / "home"
    work = home / "work dir"
    other = home / "main" / "main.bean"
    work.mkdir(parents=True)
    other.parent.mkdir()
    other.write_text(OTHER_LEDGER)
    env = _env(home, str(other))
    created = (work / target) if target.endswith(".bean") else (work / target / "main.bean")

    hint, record = _init(env, work, target)
    assert created.is_file()
    starter = created.read_bytes()

    # Sanity: a bare `bea check` beside the new ledger still opens the other, broken one.
    assert _sh("bea check", env, created.parent).returncode == 1

    checked = _sh(hint, env, work)
    assert checked.returncode == 0, f"{hint!r}: {checked.stderr or checked.stdout}"

    # The add hint, completed with a real transaction, writes the new ledger only.
    add = record.removeprefix("Record purchases with ").partition(", or ")[0]
    assert add.endswith(" add transaction"), record
    added = _sh(f"{add} Lunch --date 2026-08-02 -p 'Expenses:Dining 12 USD' -p 'Assets:Checking'", env, work)
    assert added.returncode == 0, f"{add!r}: {added.stderr or added.stdout}"
    assert b"Lunch" in created.read_bytes() and created.read_bytes() != starter
    assert other.read_text() == OTHER_LEDGER
    importing = record.partition("preview a bank export with ")[2].removesuffix(".")
    assert importing == add.removesuffix("add transaction") + "import", record


@pytest.mark.parametrize("bea_file", [None, ""])
def test_hint_is_unchanged_without_bea_file(tmp_path: Path, bea_file: str | None) -> None:
    home = tmp_path / "home"
    work = home / "work"
    work.mkdir(parents=True)
    env = _env(home, bea_file)

    hint, record = _init(env, work, "books")
    assert hint == "cd ~/work/books && bea check"
    assert record == "Record purchases with bea add transaction, or preview a bank export with bea import."
    assert _sh(hint, env, work).returncode == 0

    here, _ = _init(env, work, ".")
    assert here == "bea check"
    assert _sh(here, env, work).returncode == 0
