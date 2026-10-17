"""`price export` refuses a ledger whose URL include was refused (w5/479).

A refused include is never a source, so the export's unavailable-source
check never saw it: the snapshot kept the URL, exit 0, and stock
`bean-check` failed on it as a file glob that matches nothing.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "https://www.beancount.io/prices/BTC-USD"
LEDGER = f'option "operating_currency" "USD"\ninclude "{URL}"\n2026-01-01 open Assets:Cash USD\n'


def _export(tmp_path: Path, *flags: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k not in {"CI", "MANAGED_PRICE_ORIGINS"}}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--offline", "-f", "main.bean", "price", "export", "-o", "exp", *flags],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_the_export_is_refused_naming_the_include(tmp_path: Path) -> None:
    result = _export(tmp_path)

    assert result.returncode == 2, result.stdout + result.stderr
    assert f'Cannot export: include "{URL}" was refused:' in result.stderr
    assert "not allowlisted" in result.stderr
    assert not (tmp_path / "exp").exists()


def test_allow_errors_comments_the_include_out(tmp_path: Path) -> None:
    result = _export(tmp_path, "--allow-errors")

    assert result.returncode == 0, result.stderr
    exported = (tmp_path / "exp" / "main.bean").read_text()
    assert exported.splitlines()[1] == f"; refused URL include: {URL}"
    assert f'include "{URL}"' not in exported
    stock = subprocess.run(
        [sys.executable, "-m", "beancount.scripts.check", str(tmp_path / "exp" / "main.bean")],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert stock.returncode == 0, stock.stdout + stock.stderr
