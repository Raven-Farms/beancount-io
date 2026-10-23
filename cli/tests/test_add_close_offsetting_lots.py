"""`add close` refuses when lots cancel in units but not at cost (w5/909).

`+1 HOOL {100 USD}` and `-1 HOOL {200 USD}` are two lots the inventory keeps
apart (−100 USD at cost), but the units net to zero, so the close was taken
for a drained account and written without `--force`, with or without
`check_drained`, stranding them.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_add_close_drained_uncovered import _bea

LEDGER = """option "operating_currency" "USD"
2024-01-01 open Assets:Stock HOOL "NONE"
2024-01-01 open Assets:Cash USD
2024-02-01 * "Long"
  Assets:Stock 1 HOOL {100 USD}
  Assets:Cash -100 USD
2024-02-02 * "Short"
  Assets:Stock -1 HOOL {200 USD}
  Assets:Cash 200 USD
"""
PLUGIN = 'plugin "beancount.plugins.check_drained"\n'


def _close(tmp_path: Path, ledger: str, *flags: str) -> tuple[object, bytes]:
    path = tmp_path / "main.bean"
    path.write_text(ledger)
    before = path.read_bytes()
    result = _bea(
        tmp_path, "--json", "-f", str(path), "add", "close", "--account", "Assets:Stock", "--date", "2024-02-03", *flags
    )
    return result, before


@pytest.mark.parametrize("plugin", ["", PLUGIN], ids=["no-plugin", "check-drained"])
def test_offsetting_lots_refuse_an_unforced_close(tmp_path: Path, plugin: str) -> None:
    result, before = _close(tmp_path, plugin + LEDGER)

    assert result.returncode == 1, result.stdout  # type: ignore[attr-defined]
    message = " ".join(json.loads(result.stderr)["error"]["message"].split())  # type: ignore[attr-defined]
    assert "1 HOOL {100 USD, 2024-02-01}" in message and "-1 HOOL {200 USD, 2024-02-02}" in message
    assert "--force" in message
    assert (tmp_path / "main.bean").read_bytes() == before


def test_force_closes_with_the_lots_deliberately(tmp_path: Path) -> None:
    result, _ = _close(tmp_path, LEDGER, "--force")

    assert result.returncode == 0, result.stderr  # type: ignore[attr-defined]
    assert "close Assets:Stock" in (tmp_path / "main.bean").read_text()


def test_clearing_the_lots_first_lets_the_close_through(tmp_path: Path) -> None:
    cleared = LEDGER.replace("2024-02-03", "2024-02-03") + (
        '2024-02-03 * "Clear lots"\n  Assets:Stock -1 HOOL {100 USD, 2024-02-01}\n'
        "  Assets:Stock 1 HOOL {200 USD, 2024-02-02}\n  Assets:Cash -100 USD\n"
    )

    result, _ = _close(tmp_path, cleared)

    assert result.returncode == 0, result.stderr  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "ledger",
    [
        LEDGER.replace("{200 USD}", "{100 USD, 2024-02-01}").replace("200 USD", "100 USD"),
        LEDGER.replace("1 HOOL {100 USD}", "1 HOOL @ 100 USD").replace("-1 HOOL {200 USD}", "-1 HOOL @ 200 USD"),
    ],
    ids=["same-cost", "costless"],
)
def test_lots_that_really_cancel_close_without_force(tmp_path: Path, ledger: str) -> None:
    result, _ = _close(tmp_path, ledger)

    assert result.returncode == 0, result.stderr  # type: ignore[attr-defined]


def test_a_plain_unit_balance_keeps_its_existing_refusal(tmp_path: Path) -> None:
    result, before = _close(tmp_path, LEDGER.split('2024-02-02 * "Short"')[0])

    assert result.returncode == 1, result.stdout  # type: ignore[attr-defined]
    assert "still holds 1 HOOL" in " ".join(json.loads(result.stderr)["error"]["message"].split())  # type: ignore[attr-defined]
    assert (tmp_path / "main.bean").read_bytes() == before
