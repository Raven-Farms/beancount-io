"""Text tables print positive exponents fixed-point and NaN/Infinity by name (w5/471).

`round(number, -2)` printed `1.5E+3` and `0E+2`, and a NaN or an infinity
ended the query with an internal `TypeError` whose debug hint lacked a full
stop. CSV and JSON already printed `1500`, `0` and `Infinity`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from cli.engine import launch

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Rent USD
2026-01-01 open Expenses:Fx USD
2026-01-05 * "Landlord" "rent"
  Expenses:Rent  1500.00 USD
  Assets:Cash
2026-01-06 * "Bank" "fx fee"
  rate: "inf"
  Expenses:Fx  1.00 USD
  Assets:Cash
"""


def _query(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_a_positive_exponent_prints_its_digits_aligned(tmp_path: Path) -> None:
    result = _query(
        tmp_path, "query", "SELECT account, number, round(number, -2) AS hundreds WHERE account ~ 'Expenses'"
    )

    assert result.returncode == 0, result.stderr
    assert "E+" not in result.stdout
    rows = [line.rstrip() for line in result.stdout.splitlines()[2:]]
    assert rows == ["Expenses:Rent  1500.00  1500", "Expenses:Fx       1.00     0"]


@pytest.mark.parametrize("fmt", [(), ("-m",)])
def test_a_grouped_round_prints_fixed_point(tmp_path: Path, fmt: tuple[str, ...]) -> None:
    result = _query(tmp_path, "query", *fmt, "SELECT account, round(sum(number), -2) AS h GROUP BY account")

    assert result.returncode == 0, result.stderr
    assert "E+" not in result.stdout
    assert "-1500" in result.stdout


def test_non_finite_values_print_their_names(tmp_path: Path) -> None:
    result = _query(tmp_path, "query", "SELECT date, decimal(entry_meta('rate')) AS rate WHERE account = 'Expenses:Fx'")

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[2].split() == ["2026-01-06", "Infinity"]

    both = _query(tmp_path, "query", "SELECT decimal('NaN') AS a, decimal('-inf') AS b WHERE account = 'Expenses:Fx'")
    assert both.returncode == 0, both.stderr
    assert both.stdout.splitlines()[2].split() == ["NaN", "-Infinity"]


def test_an_engine_failure_ends_its_sentence_before_the_debug_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    envelope: dict[str, Any] = {
        "ok": False,
        "error": {"category": "validation", "message": "TypeError: no", "traceback": "Traceback ..."},
    }
    monkeypatch.setattr(launch, "helper_command", lambda: ([], {}))
    monkeypatch.setattr(launch, "_run_helper", lambda *args: None)
    monkeypatch.setattr(launch, "_parse", lambda *args, **kwargs: envelope)

    with pytest.raises(Exception) as caught:
        launch.helper_json(["query"])

    assert str(caught.value) == "TypeError: no. Pass --debug before the command for a traceback."
