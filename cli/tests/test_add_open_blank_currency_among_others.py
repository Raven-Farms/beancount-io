"""`add open` refuses a blank `-c` among others, as it refuses a lone one (w5/491).

`-c USD -c ''` dropped the blank and wrote the open with USD alone, exit 0,
though an empty value usually means a script lost a variable.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'option "operating_currency" "USD"\n'


def _open(tmp_path: Path, *currencies: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    flags = [arg for currency in currencies for arg in ("-c", currency)]
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", "main.bean", "add", "open", "--date", "2026-01-05"]
        + ["-a", "Assets:Wallet", *flags],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize(
    ("currencies", "named"), [(("USD", ""), "2 of 2"), (("  ", "USD", "EUR"), "1 of 3"), (("USD", "\t"), "2 of 2")]
)
def test_a_blank_among_others_is_refused(tmp_path: Path, currencies: tuple[str, ...], named: str) -> None:
    result = _open(tmp_path, *currencies)

    assert result.returncode == 2, result.stdout + result.stderr
    assert f"--currency value {named} is blank after trimming" in result.stderr
    assert (tmp_path / "main.bean").read_text() == LEDGER


def test_every_value_blank_keeps_its_wording(tmp_path: Path) -> None:
    result = _open(tmp_path, "")

    assert result.returncode == 2
    assert "Every --currency value is blank after trimming" in result.stderr


def test_real_currencies_still_write(tmp_path: Path) -> None:
    result = _open(tmp_path, "USD", "EUR")

    assert result.returncode == 0, result.stderr
    assert "2026-01-05 open Assets:Wallet USD,EUR" in (tmp_path / "main.bean").read_text()
