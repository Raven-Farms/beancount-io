"""A mistyped `--account`/`--default-account` is never remembered (w5/452).

A preview with `--account Assets:Savngs` (never opened) saved that account
for the header beside the real one, so every later flag-free import of the
header refused to choose between them, with no documented way to forget.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Bank USD
2026-01-01 open Expenses:Uncategorized USD
"""
MAPPING = "date=Date,narration=Description,amount=Amount"


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), "import", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def _books(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "s.csv").write_text("Date,Description,Amount\n2026-03-01,Coffee,-3.00\n")
    (tmp_path / "t.csv").write_text("Date,Description,Amount\n2026-03-02,Tea,-2.00\n")


def test_a_mistyped_account_does_not_break_flag_free_imports(tmp_path: Path) -> None:
    _books(tmp_path)
    typo = _bea(tmp_path, "s.csv", "--csv", MAPPING, "--account", "Assets:Savngs")
    assert typo.returncode == 0, typo.stderr
    assert "Not remembering these settings: Assets:Savngs is not open in this ledger." in typo.stderr
    applied = _bea(tmp_path, "s.csv", "--csv", MAPPING, "--account", "Assets:Bank", "--apply")
    assert applied.returncode == 0, applied.stderr

    flag_free = _bea(tmp_path, "t.csv")

    assert flag_free.returncode == 0, flag_free.stderr
    assert "--account Assets:Bank" in flag_free.stderr
    assert "multiple source accounts" not in flag_free.stderr


def test_a_mistyped_default_account_is_not_remembered(tmp_path: Path) -> None:
    _books(tmp_path)
    typo = _bea(tmp_path, "s.csv", "--csv", MAPPING, "--account", "Assets:Bank", "--default-account", "Expenses:Nope")
    assert typo.returncode == 0, typo.stderr
    assert "Expenses:Nope is not open" in typo.stderr
    assert not list((tmp_path / "config" / "importers").glob("csv-*.json"))


def test_the_ambiguity_refusal_names_how_to_forget(tmp_path: Path) -> None:
    _books(tmp_path)
    (tmp_path / "main.bean").write_text(LEDGER + "2026-01-01 open Assets:Savings USD\n")
    for account in ("Assets:Bank", "Assets:Savings"):
        assert _bea(tmp_path, "s.csv", "--csv", MAPPING, "--account", account).returncode == 0
    refused = _bea(tmp_path, "t.csv")
    assert refused.returncode == 2, refused.stderr
    assert "matches multiple source accounts" in refused.stderr
    record = next((tmp_path / "config" / "importers").glob("csv-*.json"))
    assert f"delete {record}" in refused.stderr
