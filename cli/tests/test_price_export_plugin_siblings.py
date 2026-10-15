"""`price export` carries the sibling modules a local plugin imports (w5/327).

w5/094 copied a plugin module beside the root but not a `helper.py` it
imports from the same directory, so the export exited 0 with a snapshot that
failed `check` on `No module named 'helper'`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
option "insert_pythonpath" "TRUE"
plugin "myplug"
2026-01-01 open Assets:Checking USD
"""
PLUGIN = """{imports}__plugins__ = ["run"]
def run(entries, options_map, config=None):
    return entries, []
"""


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
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize(
    ("imports", "expected"),
    [("import helper\n", {"main.bean", "myplug.py", "helper.py"}), ("", {"main.bean", "myplug.py"})],
    ids=["with-helper", "single-module"],
)
def test_the_snapshot_loads_with_its_plugin(tmp_path: Path, imports: str, expected: set[str]) -> None:
    books = tmp_path / "books"
    books.mkdir()
    (books / "main.bean").write_text(LEDGER)
    (books / "myplug.py").write_text(PLUGIN.format(imports=imports))
    (books / "helper.py").write_text('TEXT = "x"\n')
    (books / "unrelated.py").write_text("raise SystemExit('never imported')\n")

    exported = _bea(tmp_path, "-f", str(books / "main.bean"), "price", "export", "-o", str(tmp_path / "exp"))
    assert exported.returncode == 0, exported.stderr
    assert {path.name for path in (tmp_path / "exp").iterdir()} == expected
    check = _bea(tmp_path, "-f", str(tmp_path / "exp" / "main.bean"), "check")
    assert check.returncode == 0, check.stderr
