"""Every writer reports its destination as `target.into`, a documented target shape (w5/324).

`add` and `price export` emitted `{"file", "into"}`, a shape missing from
USAGE's target table, while `import` reported the same fact only in `data`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Uncategorized
"""
USAGE = (ROOT / "docs" / "USAGE.md").read_text()


def _target(books: Path, *args: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "--no-input", "-f", str(books / "main.bean"), *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 0, result.stderr
    return dict(json.loads(result.stdout)["target"])


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "s.csv").write_text("Date,Payee,Amount\n2026-01-05,Cafe,-3.00\n")
    return tmp_path


@pytest.mark.parametrize(
    ("args", "into"),
    [
        (("add", "note", "--date", "2026-02-01", "-a", "Assets:Checking", "-m", "hi"), "main.bean"),
        (
            ("import", "s.csv", "--csv", "date=Date,payee=Payee,amount=Amount", "--account", "Assets:Checking"),
            "main.bean",
        ),
        (("price", "export", "-o", "exp"), "exp"),
    ],
    ids=["add", "import", "price-export"],
)
def test_writers_name_their_destination_in_target_into(books: Path, args: tuple[str, ...], into: str) -> None:
    target = _target(books, *args)
    assert set(target) == {"file", "into"}
    assert Path(target["into"]).resolve() == (books / into).resolve()
    assert '`{"file": "<absolute path>", "into": "<absolute path>"}`' in USAGE


def test_readers_keep_the_file_shape(books: Path) -> None:
    assert set(_target(books, "check")) == {"file"}
