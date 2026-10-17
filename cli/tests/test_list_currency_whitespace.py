"""`list -c` matches the value it validated, surrounding whitespace removed (w5/473).

The check stripped `" HOOL"` and passed it, then the raw value was matched
and listed nothing: "No prices found.", exit 0, as if HOOL had no prices.
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
2026-01-01 open Assets:Broker HOOL
2026-01-01 commodity HOOL
2026-01-01 commodity USD
2026-01-07 price HOOL 55.25 USD
"""


def _list(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "-f", str(tmp_path / "main.bean"), "list", *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize(
    ("kind", "value", "listed"),
    [
        ("price", " HOOL", "HOOL"),
        ("price", "HOOL ", "HOOL"),
        ("price", "\thool\n", "HOOL"),
        ("commodity", " usd", "USD"),
    ],
)
def test_a_padded_currency_lists_what_it_names(tmp_path: Path, kind: str, value: str, listed: str) -> None:
    result = _list(tmp_path, kind, "-c", value)

    assert result.returncode == 0, result.stderr
    assert [row["currency"] for row in json.loads(result.stdout)["data"]] == [listed]


def test_a_space_inside_is_still_refused(tmp_path: Path) -> None:
    result = _list(tmp_path, "price", "-c", "HO OL")

    assert result.returncode == 2
