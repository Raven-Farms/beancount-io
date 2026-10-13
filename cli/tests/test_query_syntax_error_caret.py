"""The BQL syntax-error caret sits under the offending token of the text shown (w5/178).

The caret was indented by the parser's absolute offset. For a query spanning
lines that put it alone, far right of every line printed; for `FROM accounts`
or `FROM balances` in `--json` it counted the quotes the engine adds around the
table name while the text shown above it had none, so it sat two columns late.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """\
2024-01-01 open Assets:Cash
2024-01-06 * "Txn"
  Assets:Cash  1 USD
  Assets:Cash  -1 USD
"""
MULTI_LINE = 'SELECT date, narration\nFROM year = 2024\nWHERE narration = = "x"\n'


def _bea(tmp_path: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        input=stdin,
        stdin=None if stdin is not None else subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _pointed_at(lines: list[str]) -> tuple[str, str]:
    """The line the caret is under, and that line from the caret's column on."""
    carets = [index for index, line in enumerate(lines) if line.strip() == "^"]
    assert len(carets) == 1, lines
    above = lines[carets[0] - 1]
    return above.strip(), above[lines[carets[0]].index("^") :]


def _json_details(result: subprocess.CompletedProcess[str]) -> list[str]:
    assert result.returncode == 2, result.stdout + result.stderr
    details = json.loads(result.stderr)["error"]["details"]
    assert all("\n" not in detail for detail in details), details
    return [str(detail) for detail in details]


@pytest.mark.parametrize("flags", [[], ["--json"]], ids=["text", "json"])
def test_multi_line_query_gets_the_caret_under_the_token_on_its_own_line(tmp_path: Path, flags: list[str]) -> None:
    result = _bea(tmp_path, *flags, "-f", "main.bean", "query", stdin=MULTI_LINE)

    lines = _json_details(result) if flags else result.stderr.splitlines()
    assert result.returncode == 2, result.stdout + result.stderr
    # Every line of the query is shown, at one indent, and the caret follows
    # the third: under the second `=`, not 62 columns out.
    shown = [line.strip() for line in lines]
    assert shown[shown.index("SELECT date, narration") :][:4] == [
        "SELECT date, narration",
        "FROM year = 2024",
        'WHERE narration = = "x"',
        "^",
    ]
    assert _pointed_at(lines) == ('WHERE narration = = "x"', '= "x"')
    indents = {len(line) - len(line.lstrip()) for line in lines if line.strip() in MULTI_LINE.splitlines()}
    assert len(indents) == 1, lines


@pytest.mark.parametrize("table", ["accounts", "balances"])
@pytest.mark.parametrize("flags", [[], ["--json"]], ids=["text", "json"])
def test_reserved_table_name_does_not_shift_the_caret(tmp_path: Path, flags: list[str], table: str) -> None:
    result = _bea(tmp_path, *flags, "-f", "main.bean", "query", f"SELECT account FROM {table} WHERE account = = 'x'")

    lines = _json_details(result) if flags else result.stderr.splitlines()
    assert result.returncode == 2, result.stdout + result.stderr
    line, rest = _pointed_at(lines)
    assert rest == "= 'x'", lines
    assert table in line


def test_a_tab_indented_continuation_line_keeps_the_column(tmp_path: Path) -> None:
    result = _bea(
        tmp_path, "--json", "-f", "main.bean", "query", "SELECT account FROM balances WHERE\n\taccount = = 'x'"
    )

    assert _pointed_at(_json_details(result))[1] == "= 'x'"


@pytest.mark.parametrize(
    ("query", "rest"),
    [
        ("SELECT account FROM #accounts WHERE account = = 'x'", "= 'x'"),
        ("SELECT account WHERE account = = 'x'", "= 'x'"),
        # The parser ran out of input: the caret is one past the last character.
        ("SELECT account WHERE", ""),
    ],
)
def test_single_line_placement_is_unchanged(tmp_path: Path, query: str, rest: str) -> None:
    details = _json_details(_bea(tmp_path, "--json", "-f", "main.bean", "query", query))

    assert details[:2] == [f"  {query}", f"  {' ' * (len(query) - len(rest))}^"]
