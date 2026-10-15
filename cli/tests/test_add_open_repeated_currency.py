"""`add open -c` writes a repeated currency once, in first-seen order (w5/448).

Each value was appended as given, so `-c USD -c EUR -c USD` wrote
`open Assets:Z USD,EUR,USD`, while repeated `--tag` and `--link` values
collapse.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


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
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize(
    ("currencies", "written"),
    [(["USD", "EUR", "USD"], "USD,EUR"), (["USD", "USD"], "USD"), ([" EUR", "USD", "EUR "], "EUR,USD")],
)
def test_a_repeated_currency_is_written_once(tmp_path: Path, currencies: list[str], written: str) -> None:
    (tmp_path / "main.bean").write_text('option "operating_currency" "USD"\n')
    flags = [arg for currency in currencies for arg in ("-c", currency)]
    result = _bea(tmp_path, "add", "open", "--account", "Assets:Z", "--date", "2026-01-01", *flags)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "main.bean").read_text().endswith(f"2026-01-01 open Assets:Z {written}\n")
