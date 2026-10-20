"""From a removed working directory, a refusal that prints a remedy still says why (w5/837).

`bea_command` called `Path.cwd()`, which raises there, so every refusal whose
remedy names the ledger — an add with an unknown account, an import with
blocked rows — died as a bare `FileNotFoundError`, exit 1, its reason lost.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = (
    'option "operating_currency" "USD"\n2026-01-01 open Assets:Checking\n'
    "2026-01-01 open Expenses:Food USD\n2026-01-01 open Expenses:Uncategorized\n"
)
pytestmark = pytest.mark.skipif(sys.platform == "win32" or shutil.which("bash") is None, reason="POSIX shell")


def _from_removed_cwd(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
        # The checkout venv's logfire registers a pydantic plugin that resolves
        # the working directory on import; the managed engine carries none.
        PYDANTIC_DISABLE_PLUGINS="__all__",
    )
    gone = tmp_path / "gone"
    gone.mkdir()
    command = shlex.join([sys.executable, "-m", "cli.main", *args])
    script = f"cd {shlex.quote(str(gone))} && rmdir {shlex.quote(str(gone))} && exec {command}"
    return subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True, timeout=120, check=False)


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    (tmp_path / "books").mkdir()
    path = tmp_path / "books" / "main.bean"
    path.write_text(LEDGER)
    return path


def test_an_unknown_account_add_names_its_reason(tmp_path: Path, ledger: Path) -> None:
    result = _from_removed_cwd(
        tmp_path,
        "--file",
        str(ledger),
        "add",
        "transaction",
        "Latte",
        "--date",
        "2026-04-01",
        "-p",
        "Expenses:Coffee 4 USD",
        "-p",
        "Assets:Checking",
    )

    assert result.returncode == 1, result.stderr
    said = " ".join(result.stderr.split())
    assert "unknown account 'Expenses:Coffee'" in said
    assert f"bea --file {ledger} add open --account Expenses:Coffee" in said
    assert "FileNotFoundError" not in said
    assert ledger.read_text() == LEDGER


def test_an_import_with_blocked_rows_still_previews(tmp_path: Path, ledger: Path) -> None:
    (tmp_path / "bank.csv").write_text("Date,Description,Amount\n2026-03-01,Coffee,-3.50\n")

    result = _from_removed_cwd(
        tmp_path,
        "--json",
        "--file",
        str(ledger),
        "import",
        str(tmp_path / "bank.csv"),
        "--csv",
        "date=Date,amount=Amount,narration=Description",
        "--account",
        "Assets:Checking",
        "--default-account",
        "Expenses:Coffee",
    )

    assert result.returncode == 0, result.stderr
    (row,) = json.loads(result.stdout)["data"]["rows"]
    assert row["status"] == "blocked"
    assert "FileNotFoundError" not in result.stderr
