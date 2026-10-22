"""A preset opening on `0001-01-01` explains the missing prior day (w5/889).

The opening posts the day before the history starts; for the first
representable day that subtraction raised a bare `OverflowError`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_init_preset import _bea

FIRST = ["--preset", "personal@1", "--currency", "USD"]


@pytest.mark.parametrize("as_json", [True, False], ids=["json", "human"])
def test_a_known_opening_on_the_first_day_is_a_usage_refusal(tmp_path: Path, as_json: bool) -> None:
    result = _bea(
        tmp_path,
        *(["--json"] if as_json else []),
        "init",
        str(tmp_path / "nested" / "books"),
        *FIRST,
        "--date",
        "0001-01-01",
        "--opening-balance",
        "Assets:Cash 100",
    )

    assert result.returncode == 2, result.stdout + result.stderr
    said = json.loads(result.stderr)["error"]["message"] if as_json else result.stderr
    flat = " ".join(said.split())
    assert "--date 0001-01-01" in flat and "0001-01-02 or later" in flat
    assert "OverflowError" not in flat and "Traceback" not in said
    assert not (tmp_path / "nested").exists()


@pytest.mark.parametrize(
    "extra",
    [
        ["--date", "0001-01-02", "--opening-balance", "Assets:Cash 100"],
        ["--date", "0001-01-01"],
        ["--date", "0001-01-01", "--opening-balance", "Assets:Cash 0"],
    ],
    ids=["next-day-known", "first-day-unknown", "first-day-zero"],
)
def test_the_neighbouring_inputs_still_create_checked_ledgers(tmp_path: Path, extra: list[str]) -> None:
    books = tmp_path / "books"
    created = _bea(tmp_path, "--json", "init", str(books), *FIRST, *extra)

    assert created.returncode == 0, created.stderr
    assert _bea(tmp_path, "--json", "--file", str(books / "main.bean"), "check").returncode == 0
