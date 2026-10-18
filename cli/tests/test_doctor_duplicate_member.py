"""`bea doctor` refuses a file included under two names, as `check` does (w5/569).

Upstream compares include paths as text, so a file reached under two names
(a link, or another letter case on a volume that ignores it) loaded twice:
`linked` reported one 3.00 lunch as `Net Income: (-6.00 USD)`, and
`roundtrip` crashed with a `CompareError` traceback.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    books = tmp_path / "books"
    (books / "Sub").mkdir(parents=True)
    (books / "Sub" / "X.bean").write_text('2026-01-05 * "lunch" ^l\n  Expenses:Food  3.00 USD\n  Assets:Cash\n')
    (books / "alias.bean").symlink_to("Sub/X.bean")
    main = books / "main.bean"
    main.write_text(
        'include "Sub/X.bean"\ninclude "alias.bean"\n'
        "2026-01-01 open Assets:Cash USD\n2026-01-01 open Expenses:Food USD\n"
    )
    return main


@pytest.mark.parametrize("op", [["linked", "{ledger}", "^l"], ["roundtrip", "{ledger}"], ["missing-open", "{ledger}"]])
def test_doctor_refuses_with_checks_duplicate_include_line(tmp_path: Path, ledger: Path, op: list[str]) -> None:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )

    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "doctor", *(part.format(ledger=ledger) for part in op)],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert f"{ledger}:2: Duplicate include: {ledger.parent / 'alias.bean'} is" in result.stderr, result.stderr
    assert "6.00" not in result.stdout and "Traceback" not in result.stderr
