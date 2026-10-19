"""Under `unique_prices`, a same-day price conflict points at the existing quote instead of `--force` (w5/397).

The refusal offered `--force`, and the forced write then failed on the
plugin's bare "Disagreeing price entries" without naming it.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = 'plugin "beancount.plugins.unique_prices"\n'
LEDGER = """option "operating_currency" "USD"
2026-01-01 commodity USD
2026-01-01 commodity EUR
2026-01-05 price EUR 1.1 USD
"""
PRICE = ("add", "price", "--date", "2026-01-05", "-c", "EUR", "--amount", "1.2 USD")


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
        [sys.executable, "-m", "cli.main", *args],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize("force", [(), ("--force",)], ids=["plain", "forced"])
def test_conflict_under_unique_prices_names_the_plugin_and_the_existing_line(
    tmp_path: Path, force: tuple[str, ...]
) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(PLUGIN + LEDGER)
    before = ledger.read_bytes()
    result = _bea(tmp_path, "-f", str(ledger), *PRICE, *force)

    assert result.returncode == 4, result.stderr
    assert ledger.read_bytes() == before
    flat = " ".join(result.stderr.split())
    assert f"EUR already has a 2026-01-05 price of 1.1 USD (at {ledger}:5); refusing 1.2 USD." in flat
    assert "unique_prices" in flat
    assert f"edit the existing price at {ledger}:5 instead" in flat
    assert "--force" not in flat
    assert "Disagreeing price entries" not in flat


PEDANTIC = """option "operating_currency" "USD"
plugin "beancount.plugins.pedantic"
2026-01-01 commodity USD
2026-01-01 commodity EUR
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD
2026-01-02 * "use"
  Assets:Cash  -1.00 USD
  Expenses:Food
2026-01-05 price EUR 1.1 USD
"""


@pytest.mark.parametrize("force", [(), ("--force",)], ids=["plain", "forced"])
def test_conflict_under_pedantic_names_the_bundle_and_the_existing_line(tmp_path: Path, force: tuple[str, ...]) -> None:
    """pedantic bundles unique_prices, so --force advice would fail the same way (w5/766)."""
    ledger = tmp_path / "main.bean"
    ledger.write_text(PEDANTIC)
    before = ledger.read_bytes()
    result = _bea(tmp_path, "-f", str(ledger), *PRICE, *force)

    assert result.returncode == 4, result.stderr
    assert ledger.read_bytes() == before
    flat = " ".join(result.stderr.split())
    assert "EUR already has a 2026-01-05 price of 1.1 USD" in flat
    assert "the pedantic plugin (which bundles unique_prices)" in flat
    assert "edit the existing price at" in flat
    assert "Pass --force to record another quote." not in flat
    assert "Disagreeing price entries" not in flat


def test_without_the_plugin_force_still_records_another_quote(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    refused = _bea(tmp_path, "-f", str(ledger), *PRICE)
    assert refused.returncode == 4, refused.stderr
    assert "Pass --force to record another quote." in " ".join(refused.stderr.split())

    forced = _bea(tmp_path, "-f", str(ledger), *PRICE, "--force")
    assert forced.returncode == 0, forced.stderr
    assert " ".join(ledger.read_text().split()).endswith("2026-01-05 price EUR 1.2 USD")
