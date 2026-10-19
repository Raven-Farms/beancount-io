"""Compound costs hash distinctly, legs sort numerically (w5/742).

The lot hash used `number_per` alone, so `{100 # 5 USD}` and `{100 # 10
USD}` shared one id and the second buy was skipped as an exact duplicate —
and the preview showed `{100 USD}`, neither lot's real cost. Legs sort by
numeric amount, then commodity, then lot, while dedup.md said "sorted
order". Compound lots now count at their effective per-unit cost, in the
hash and the preview, with the per-only spelling as a lot-gated lookup-only
key so earlier imports still match.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

HEADER = """\
option "operating_currency" "USD"
2026-01-01 open Assets:Broker:AAPL AAPL
2026-01-01 open Assets:Broker:Cash USD
2026-01-01 open Equity:Opening
2026-01-02 * "Fund"
  Assets:Broker:Cash  10000 USD
  Equity:Opening
"""

IMPORTER = """\
import datetime, json
from decimal import Decimal
from beancount.core import amount, data


class Rows:
    name = "rows"

    def identify(self, filepath):
        return filepath.endswith(".rows")

    def account(self, filepath):
        return "Assets:Broker:AAPL"

    def extract(self, filepath, existing):
        out = []
        for line, row in enumerate(json.load(open(filepath)), start=1):
            postings = []
            for leg in row["legs"]:
                cost = None
                if leg.get("per") is not None or leg.get("total") is not None:
                    per = Decimal(leg["per"]) if leg.get("per") is not None else None
                    total = Decimal(leg["total"]) if leg.get("total") is not None else None
                    cost = data.CostSpec(per, total, "USD", None, None, False)
                postings.append(
                    data.Posting(
                        "Assets:Broker:AAPL", amount.Amount(Decimal(leg["units"]), "AAPL"),
                        cost, None, None, None,
                    )
                )
            postings.append(
                data.Posting(
                    "Assets:Broker:Cash", amount.Amount(Decimal(row["cash"]), "USD"),
                    None, None, None, None,
                )
            )
            out.append(
                data.Transaction(
                    data.new_metadata(filepath, line),
                    datetime.date.fromisoformat(row["date"]),
                    "*", None, row["narration"], data.EMPTY_SET, data.EMPTY_SET, postings,
                )
            )
        return out


CONFIG = [Rows()]
"""

A_ROWS = (
    '[{"date": "2026-05-07", "narration": "BUY AAPL", "cash": "-505", '
    '"legs": [{"units": "5", "per": "100", "total": "5"}]}]'
)
B_ROWS = (
    '[{"date": "2026-05-07", "narration": "BUY AAPL", "cash": "-510", '
    '"legs": [{"units": "5", "per": "100", "total": "10"}]}]'
)


def _setup(tmp_path: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(HEADER)
    (tmp_path / "imp.py").write_text(IMPORTER)
    (tmp_path / "a.rows").write_text(A_ROWS)
    (tmp_path / "b.rows").write_text(B_ROWS)
    return path


def _import(path: Path, rows: str, *args: str) -> Any:
    return runner.invoke(
        app,
        ["--json", "--no-input", "--file", str(path), "import", str(path.parent / rows)]
        + ["--config", str(path.parent / "imp.py"), *args],
    )


def _rows(result: Any) -> list[dict[str, Any]]:
    assert result.exit_code == 0, result.output
    return json.loads(result.output)["data"]["rows"]


def test_different_compound_costs_are_different_rows(tmp_path: Path) -> None:
    path = _setup(tmp_path)

    applied = _import(path, "a.rows", "--apply")

    assert applied.exit_code == 0, applied.output
    assert "csv:sha256:a5b6e00ea85caa3d" in path.read_text()
    assert "5 AAPL {100 # 5 USD}" in path.read_text()

    preview = runner.invoke(
        app,
        ["--no-input", "--file", str(path), "import", str(tmp_path / "b.rows")]
        + ["--config", str(tmp_path / "imp.py")],
    )
    assert preview.exit_code == 0, preview.output
    assert "5 AAPL {102 USD}" in preview.output, preview.output

    applied = _import(path, "b.rows", "--apply")

    assert applied.exit_code == 0, applied.output
    assert "csv:sha256:9d7461ecc4d9af56" in path.read_text()
    assert path.read_text().count("BUY AAPL") == 2


def test_a_compound_row_reimport_stays_a_duplicate(tmp_path: Path) -> None:
    path = _setup(tmp_path)
    assert _import(path, "a.rows", "--apply").exit_code == 0

    again = _import(path, "a.rows", "--apply")

    assert again.exit_code == 0, again.output
    (row,) = _rows(again)
    assert row["status"] == "duplicate", row
    assert path.read_text().count("BUY AAPL") == 1


def test_a_legacy_per_only_id_still_matches(tmp_path: Path) -> None:
    path = _setup(tmp_path)
    with path.open("a", encoding="utf-8") as ledger:
        ledger.write(
            '\n2026-05-07 * "BUY AAPL"\n'
            '  import-id: "csv:sha256:f24c082abb6572b0"\n'
            "  Assets:Broker:AAPL      5 AAPL {100 # 5 USD}\n"
            "  Assets:Broker:Cash  -505.00 USD\n"
        )

    again = _import(path, "a.rows", "--apply")

    assert again.exit_code == 0, again.output
    (row,) = _rows(again)
    assert row["status"] == "duplicate", row
    assert path.read_text().count("BUY AAPL") == 1

    new = _import(path, "b.rows", "--apply")

    assert new.exit_code == 0, new.output
    (row,) = _rows(new)
    assert row["status"] == "new", row
    assert path.read_text().count("BUY AAPL") == 2


def test_two_legs_hash_in_numeric_order(tmp_path: Path) -> None:
    path = _setup(tmp_path)
    (tmp_path / "c.rows").write_text(
        '[{"date": "2026-05-07", "narration": "BUY AAPL", "cash": "-1400", '
        '"legs": [{"units": "10", "per": "120"}, {"units": "2", "per": "100"}]}]'
    )

    applied = _import(path, "c.rows", "--apply")

    assert applied.exit_code == 0, applied.output
    # Numeric order, as dedup.md now states: string sorting would hash
    # `10 AAPL …+2 AAPL …` instead.
    assert "csv:sha256:6648ad67a6d94d97" in path.read_text()
