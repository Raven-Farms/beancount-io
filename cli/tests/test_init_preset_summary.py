"""The human summary of `init --preset` describes the files it wrote (w5/877).

A blank preset opens nothing but was reported as the 14-account chart, and an
opening balance moves the opens to the day before the boundary while the text
still said the boundary date.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from tests.test_init_preset import _bea

FLAGS = ["--currency", "USD", "--date", "2024-02-01"]


def _opens(tmp_path: Path, name: str) -> list[dict]:
    listed = _bea(tmp_path, "--json", "--file", str(tmp_path / name / "main.bean"), "list", "open")
    assert listed.returncode == 0, listed.stderr
    return json.loads(listed.stdout)["data"]


def _init(tmp_path: Path, name: str, *args: str) -> str:
    created = _bea(tmp_path, "init", str(tmp_path / name), *args)
    assert created.returncode == 0, created.stderr or created.stdout
    return created.stdout


def test_a_blank_preset_claims_no_accounts(tmp_path: Path) -> None:
    said = _init(tmp_path, "blank", "--preset", "blank@1", *FLAGS)

    assert _opens(tmp_path, "blank") == []
    assert "with 0 accounts" in said
    assert "Accounts open on" not in said


def test_a_clean_preset_counts_and_dates_match_the_listing(tmp_path: Path) -> None:
    said = _init(tmp_path, "personal", "--preset", "personal@1", *FLAGS)

    opens = _opens(tmp_path, "personal")
    assert f"with {len(opens)} accounts" in said
    assert {row["date"] for row in opens} == {"2024-02-01"}
    assert "Accounts open on 2024-02-01." in said


def test_a_known_opening_reports_the_day_the_accounts_open(tmp_path: Path) -> None:
    said = _init(tmp_path, "known", "--preset", "personal@1", *FLAGS, "--opening-balance", "Assets:Cash 100")

    opens = _opens(tmp_path, "known")
    assert f"with {len(opens)} accounts" in said
    assert {row["date"] for row in opens} == {"2024-01-31"}
    assert "Accounts open on 2024-01-31." in said


def test_the_fixed_chart_keeps_its_summary(tmp_path: Path) -> None:
    said = _init(tmp_path, "legacy", *FLAGS)

    assert re.search(r"with 14 accounts", said)
    assert "Accounts open on 2024-02-01." in said
