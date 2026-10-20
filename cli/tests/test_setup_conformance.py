"""Cross-engine conformance: `bea init --preset` opens what the catalog fixture promises.

The hosted builder (backend-v2) and this CLI must produce equivalent
accounting results for every fixture before a preset is listed (ADR021).
These tests run the CLI side against the canonical fixtures and compare the
opened accounts; the hosted side is asserted in backend-v2's setup tests
against the same fixture file.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_FIXTURES = (
    ROOT.parent / "backend-cluster" / "backend-v2" / "src" / "features" / "ledger" / "setup" / "fixtures.json"
)


def _fixtures() -> list[dict]:
    if not CANONICAL_FIXTURES.is_file():
        pytest.skip("canonical backend fixtures not present in this checkout")
    return json.loads(CANONICAL_FIXTURES.read_text(encoding="utf-8"))["fixtures"]


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
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
        timeout=30,
    )


def test_clean_fixtures_open_the_promised_accounts(tmp_path: Path) -> None:
    clean = [fixture for fixture in _fixtures() if fixture["id"].endswith("-clean")]
    assert len(clean) == 8
    for fixture in clean:
        books = tmp_path / fixture["id"].replace("@", "-")
        result = _bea(
            tmp_path,
            "--json",
            "init",
            str(books),
            "--preset",
            fixture["spec"]["preset"],
            "--currency",
            fixture["spec"]["operatingCurrency"],
            "--date",
            fixture["spec"]["historyStart"],
        )
        assert result.returncode == 0, (fixture["id"], result.stderr or result.stdout)
        opened = set(json.loads(result.stdout)["data"]["accounts"])
        assert opened == set(fixture["expected"]["openedAccounts"]), fixture["id"]
        # A clean fixture carries no transactions and no assertions.
        ledger = (books / "main.bean").read_text(encoding="utf-8")
        assert " balance " not in ledger, fixture["id"]
        assert ' * "' not in ledger, fixture["id"]


def test_opening_fixture_matches_hosted_expectations(tmp_path: Path) -> None:
    fixture = next(f for f in _fixtures() if f["id"] == "personal@1-opening-known")
    books = tmp_path / "books"
    result = _bea(
        tmp_path,
        "--json",
        "init",
        str(books),
        "--preset",
        "personal@1",
        "--currency",
        "EUR",
        "--date",
        "2026-02-01",
        "--opening-balance",
        "Assets:Cash 100",
    )
    assert result.returncode == 0, result.stderr or result.stdout
    ledger = (books / "main.bean").read_text(encoding="utf-8")
    assert f"{fixture['expected']['openingTransactionDate']} *" in ledger
    assert f"{fixture['expected']['balanceAssertionDate']} balance Assets:Cash" in ledger
    checked = _bea(tmp_path, "--file", str(books / "main.bean"), "check")
    assert checked.returncode == 0, checked.stderr or checked.stdout
