"""`doctor linked` resolves an include-relative `file:start:end` region, as it does `file:line` (w5/494).

The w5/062 split read one trailing field for `linked`, so
`txns/jan.bean:1:7` was taken as file `txns/jan.bean:1`, forwarded
unresolved, and matched no entries.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("location", ["txns/jan.bean:1:7", "txns/jan.bean:1"])
def test_linked_resolves_from_outside_the_books(tmp_path: Path, location: str) -> None:
    (tmp_path / "books" / "txns").mkdir(parents=True)
    (tmp_path / "books" / "main.bean").write_text(
        'include "txns/jan.bean"\n2024-01-01 open Assets:Cash USD\n2024-01-01 open Expenses:Food USD\n'
    )
    (tmp_path / "books" / "txns" / "jan.bean").write_text(
        '2024-01-05 * "a" ^grp\n  Expenses:Food  10 USD\n  Assets:Cash\n\n'
        '2024-01-06 * "b" ^grp\n  Expenses:Food  5 USD\n  Assets:Cash\n'
    )
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )

    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "doctor", "linked", "books/main.bean", location],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Net Income: (-15 USD)" in result.stdout
