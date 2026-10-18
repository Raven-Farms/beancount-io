"""Concurrent `add balance` runs record one assertion, not one each (w5/115).

`add balance` decided "already recorded?" and "needs --force?" against a
snapshot it then dropped, so the append captured a fresh one under the lock and
could not see that another writer had landed in between. Writers started
together all exited 0 and the ledger held an assertion apiece, which the same
commands run one after the other refuse.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """\
option "operating_currency" "USD"
include "extra.bean"
2026-01-01 open Assets:Checking USD
2026-01-01 open Equity:Opening USD

2026-01-02 * "Opening"
  Assets:Checking  1000.00 USD
  Equity:Opening  -1000.00 USD
"""
WRITERS = 4


def _env(tmp_path: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return env


def _ledger(tmp_path: Path) -> Path:
    (tmp_path / "extra.bean").write_text("", encoding="utf-8")
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")
    return ledger


def _command(ledger: Path, *args: str) -> list[str]:
    return [sys.executable, "-m", "cli.main", "--json", "--file", str(ledger), "add", "balance", *args]


def _race(tmp_path: Path, ledger: Path, runs: list[list[str]]) -> list[tuple[int, str, str]]:
    """Start every run at once and return each one's exit code, stdout and stderr."""
    env = _env(tmp_path)
    processes = [
        subprocess.Popen(
            _command(ledger, *args),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for args in runs
    ]
    results = []
    for process in processes:
        try:
            out, err = process.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            for other in processes:
                other.kill()
            raise
        results.append((process.returncode, out, err))
    return results


def _assertions(tmp_path: Path) -> list[str]:
    text = (tmp_path / "main.bean").read_text(encoding="utf-8") + (tmp_path / "extra.bean").read_text(encoding="utf-8")
    return [line for line in text.splitlines() if " balance Assets:Checking" in line]


BALANCE = ["--date", "2026-03-01", "--account", "Assets:Checking", "--amount"]


@pytest.mark.parametrize(
    "runs",
    [
        pytest.param([[*BALANCE, "1000 USD"]] * WRITERS, id="identical"),
        pytest.param([[*BALANCE, amount] for amount in ("1000 USD", "1000.00 USD") * (WRITERS // 2)], id="precision"),
        pytest.param(
            [[*BALANCE, "1000 USD", *into] for into in ([], ["--into", "extra.bean"]) * (WRITERS // 2)], id="into"
        ),
        pytest.param(
            [[*BALANCE, "1000 USD", "--pad-from", "Equity:Opening", "--pad-date", "2026-02-01"]] * WRITERS,
            id="pad-from",
        ),
    ],
)
def test_concurrent_add_balance_records_one_assertion(tmp_path: Path, runs: list[list[str]]) -> None:
    ledger = _ledger(tmp_path)

    results = _race(tmp_path, ledger, runs)

    report = "\n".join(f"exit {code}: {out.strip()} {err.strip()}" for code, out, err in results)
    assert len(_assertions(tmp_path)) == 1, report
    wrote = 0
    for code, out, err in results:
        if code == 0:
            # The winner, or a writer that ran after it and found the assertion recorded.
            payload = json.loads(out)["data"]
            assert payload["written"] == 1 or payload.get("duplicate") is True, report
            wrote += payload["written"]
        else:
            # A competing snapshot or a different precision is a conflict.
            assert code == 4, report
            assert "changed" in err or "Pass --force to record another assertion" in err, report
    assert wrote == 1, report


def test_sequential_add_balance_still_reports_the_duplicate_and_the_refusal(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)

    first, same, other = (
        _race(tmp_path, ledger, [[*BALANCE, amount]])[0] for amount in ("1000 USD", "1000 USD", "1000.00 USD")
    )

    assert first[0] == 0 and json.loads(first[1])["data"]["written"] == 1, first
    assert same[0] == 0 and json.loads(same[1])["data"]["duplicate"] is True, same
    assert other[0] == 4 and "Pass --force to record another assertion" in other[2], other
    assert len(_assertions(tmp_path)) == 1


@pytest.mark.parametrize(
    "extra",
    [
        pytest.param({}, id="plain"),
        pytest.param({"into": "extra.bean"}, id="into"),
        pytest.param({"request": {"pad_from": "Equity:Opening", "pad_date": "2026-02-01"}}, id="pad-from"),
    ],
)
def test_a_writer_landing_after_the_duplicate_check_is_a_conflict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, extra: dict[str, Any]
) -> None:
    """The race, pinned: another writer's assertion arrives right after the "already recorded?" check."""
    from bea_engine import protocol
    from bea_engine.ledger import adding

    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    ledger = _ledger(tmp_path)
    checked = adding._balance_match

    def check_then_lose_the_race(*args: Any) -> Any:
        match = checked(*args)
        with ledger.open("a", encoding="utf-8") as handle:
            handle.write("2026-03-01 balance Assets:Checking 1000 USD\n")
        return match

    monkeypatch.setattr(adding, "_balance_match", check_then_lose_the_race)
    request = {"date": "2026-03-01", "account": "Assets:Checking", "amount": "1000 USD", **extra.get("request", {})}
    into = tmp_path / extra["into"] if "into" in extra else None

    with pytest.raises(protocol.ConflictError, match="changed"):
        adding.answer(ledger, "balance", request, into=into)

    assert len(_assertions(tmp_path)) == 1
