"""Note and document tags and links print like a transaction's in the text table (w5/179).

`SELECT tags, links FROM #notes` (and `#documents`) printed the Python repr
`frozenset({'work', 'tax', 'trip'})`, in hash order, because those columns are
typed `frozenset[str]` and upstream's text renderer only knows `set`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """\
2024-01-01 open Assets:Cash
2024-01-02 note Assets:Cash "plain note"
2024-01-03 note Assets:Cash "tagged note" #trip #tax #work ^inv-1
2024-01-05 document Assets:Cash "docs/a.pdf" #trip #tax #work ^inv-1
2024-01-06 * "Txn" #trip #tax #work ^inv-1
  Assets:Cash  1 USD
  Assets:Cash  -1 USD
"""
SEEDS = ["1", "2", "3", "7", "11"]


def _bea(tmp_path: Path, seed: str, *args: str, stdin: str | None = None) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        PYTHONHASHSEED=seed,
        NO_COLOR="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--file", str(tmp_path / "main.bean"), *args],
        env=env,
        input=stdin,
        stdin=None if stdin is not None else subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def _ledger(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.pdf").touch()
    (tmp_path / "main.bean").write_text(LEDGER)


def _cells(table: str) -> list[list[str]]:
    """The data rows of a text table, split on its two-space column gutter by header offsets."""
    header, rule, *rows = table.rstrip("\n").split("\n")
    spans, start = [], 0
    for dashes in rule.split("  "):
        spans.append((start, start + len(dashes)))
        start += len(dashes) + 2
    assert [header[a:b].strip() for a, b in spans] == ["date", "tags", "links"]
    return [[row[a:b].rstrip() for a, b in spans] for row in rows]


@pytest.mark.parametrize(
    ("table", "expected"),
    [
        ("#notes", [["2024-01-02", "", ""], ["2024-01-03", "tax  trip  work", "inv-1"]]),
        ("#documents", [["2024-01-05", "tax  trip  work", "inv-1"]]),
        # Control: the transaction columns were always rendered this way.
        ("#transactions", [["2024-01-06", "tax  trip  work", "inv-1"]]),
    ],
)
def test_text_table_prints_sorted_tags_and_links_under_every_seed(
    tmp_path: Path, table: str, expected: list[list[str]]
) -> None:
    _ledger(tmp_path)
    query = f"SELECT date, tags, links FROM {table}"

    outputs = {seed: _bea(tmp_path, seed, "query", query) for seed in SEEDS}

    assert len(set(outputs.values())) == 1, outputs
    assert "frozenset" not in outputs["1"]
    assert _cells(outputs["1"]) == expected


def test_piped_shell_statement_prints_the_same_cells(tmp_path: Path) -> None:
    _ledger(tmp_path)

    output = _bea(tmp_path, "3", "query", stdin="SELECT date, tags, links FROM #notes;\n")

    assert "frozenset" not in output
    assert "2024-01-03  tax  trip  work  inv-1" in output
