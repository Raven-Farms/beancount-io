"""`query` text tables pad cells by display width, not character count (w5/751).

A CJK payee counted 9 characters but drew 18 columns, so that row's
numbers sat under the next column and the row ran past the table. Cells
are measured and padded by the columns they draw.
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from beanquery import query_render
from beanquery.cursor import Column

from bea_engine.query import _fixed_point_text, _render_text_display_width, result_context
from cli.output import display_width

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """\
option "operating_currency" "USD"
2026-01-01 open Assets:Cash
2026-01-01 open Expenses:Food
2026-01-01 open Equity:Opening
2026-01-04 txn "Cafe Bistro Paris" "Lunch"
  Expenses:Food  100.00 USD
  Assets:Cash
2026-01-05 txn "東京ラーメン屋さん" "Dinner"
  Expenses:Food  12.34 USD
  Assets:Cash
"""

QUERY = "SELECT date, payee, position, balance WHERE account = 'Expenses:Food'"


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        HOME=str(tmp_path / "home"),
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
        timeout=60,
    )


def _start(line: str, needle: str, last: bool = False) -> int:
    """The display column a cell starts at."""
    index = line.rindex if last else line.index
    return display_width(line[: index(needle)])


def _end(line: str, needle: str, last: bool = False) -> int:
    """The display column a cell ends at."""
    return _start(line, needle, last) + display_width(needle)


def test_a_cjk_payee_keeps_its_row_aligned(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")

    result = _bea(tmp_path, "--file", str(ledger), "query", QUERY)

    assert result.returncode == 0, result.stdout + result.stderr
    rows = [line for line in result.stdout.splitlines() if line.startswith("2026-")]
    assert len(rows) == 2, result.stdout
    latin, cjk = rows
    assert display_width(latin) == display_width(cjk), result.stdout
    assert _start(latin, "100.00 USD") + 3 == _start(cjk, "12.34 USD") + 2, result.stdout
    assert _end(latin, "100.00 USD") == _end(cjk, "12.34 USD"), result.stdout
    assert _end(latin, "100.00 USD", last=True) == _end(cjk, "112.34 USD"), result.stdout


@pytest.mark.parametrize(
    "options",
    [{}, {"boxed": True}, {"boxed": True, "unicode": True}, {"spaced": True}, {"narrow": False}],
    ids=["plain", "boxed", "boxed-unicode", "spaced", "wide-headers"],
)
def test_text_rendering_matches_upstream_on_ascii(options: dict[str, bool]) -> None:
    """bea's display-width table is upstream's table where widths agree (w5/751)."""
    columns = [Column("name", str), Column("amount", Decimal), Column("day", date), Column("note", object)]
    rows = [
        ("Cash", Decimal("100.50"), date(2026, 1, 4), "plain"),
        ("Food", Decimal("-4.25"), date(2026, 1, 5), "two\nlines"),
        ("Misc", None, None, None),
    ]
    dcontext = result_context(rows)

    shown: dict[str, str] = {}
    with _fixed_point_text():
        for label, render in (("upstream", query_render.render_text), ("bea", _render_text_display_width)):
            out = io.StringIO()
            if label == "upstream":
                render(columns, rows, dcontext, out, **options)  # type: ignore[arg-type]
            else:
                render(columns, rows, out, dcontext=dcontext, **options)
            shown[label] = out.getvalue()

    assert shown["bea"] == shown["upstream"]
