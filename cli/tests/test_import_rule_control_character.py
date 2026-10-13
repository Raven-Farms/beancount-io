"""A rule whose `match` holds a control character is refused (w5/132).

In a double-quoted TOML string `\\b` is a backspace and `\\t` a tab, so the
natural word-boundary rule `match = "\\bshell\\b"` compiled to a pattern no
bank text can match. The import exited 0 and filed every row under the default
account. Such a rule is now a usage error naming the rule and the single-quote
remedy, and the escapes TOML itself rejects (`"oil \\d+"`) carry the same hint.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Fuel
2026-01-01 open Expenses:Uncategorized
"""
CSV = "Date,Description,Amount\n2026-08-02,SHELL OIL 123,-40.00\n2026-08-03,SEASHELL CAFE,-9.99\n"
REMEDY = "write the regex in single quotes (match = '\\bshell\\b') or double each backslash"


@pytest.fixture
def ledger(tmp_path: Path, bea_config_dir: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(LEDGER)
    (tmp_path / "s.csv").write_text(CSV)
    return path


def _import(ledger: Path, match_line: str) -> tuple[int, dict[str, Any]]:
    rules = ledger.parent / "r.toml"
    rules.write_text(f'[[rule]]\n{match_line}\naccount = "Expenses:Fuel"\n')
    source = str(ledger.parent / "s.csv")
    argv = ["--json", "--no-input", "--file", str(ledger), "import", source]
    result = CliRunner().invoke(app, [*argv, "--account", "Assets:Checking", "--rules", str(rules), "--apply"])
    stream = result.stdout if result.exit_code == 0 else result.stderr
    return result.exit_code, json.loads(stream)


@pytest.mark.parametrize(
    ("match_line", "shown"),
    [
        ('match = "\\bshell\\b"', "'\\x08shell\\x08' contains the control character '\\x08'"),
        ('match = "shell\\toil"', "'shell\\toil' contains the control character '\\t'"),
        # A lone escape is whitespace-only; it must not read as "empty match".
        ('match = "\\t"', "'\\t' contains the control character '\\t'"),
    ],
)
def test_a_toml_escape_in_a_match_is_refused(ledger: Path, match_line: str, shown: str) -> None:
    code, payload = _import(ledger, match_line)

    assert code == 2
    message = payload["error"]["message"]
    assert f"Rule 1 match {shown}, so it can never match." in message
    assert REMEDY in message
    assert ledger.read_text() == LEDGER


@pytest.mark.parametrize("match_line", ["match = '\\bshell\\b'", 'match = "\\\\bshell\\\\b"'])
def test_the_literal_and_doubled_spellings_match_on_the_word_boundary(ledger: Path, match_line: str) -> None:
    code, payload = _import(ledger, match_line)

    assert code == 0
    assert [row["rule"] for row in payload["data"]["rows"]] == ["\\bshell\\b", "unmatched"]
    written = ledger.read_text()
    assert '2026-08-02 * "SHELL OIL 123"' in written
    assert '2026-08-03 ! "SEASHELL CAFE"' in written


def test_an_escape_toml_rejects_carries_the_same_remedy(ledger: Path) -> None:
    code, payload = _import(ledger, 'match = "oil \\d+"')

    assert code == 2
    message = payload["error"]["message"]
    assert "Unescaped '\\' in a string" in message
    assert REMEDY in message
    assert ledger.read_text() == LEDGER


def test_another_toml_error_gets_no_backslash_hint(ledger: Path) -> None:
    code, payload = _import(ledger, "match = ")

    assert code == 2
    assert "Cannot parse rules file" in payload["error"]["message"]
    assert REMEDY not in payload["error"]["message"]


def test_the_engine_copy_refuses_the_same_rule(tmp_path: Path) -> None:
    from bea_engine.csv_mapper import load_rules
    from bea_engine.protocol import UsageError

    rules = tmp_path / "r.toml"
    rules.write_text('[[rule]]\nmatch = "\\bshell\\b"\naccount = "Expenses:Fuel"\n')

    with pytest.raises(UsageError) as refusal:
        load_rules(rules)

    assert "Rule 1 match '\\x08shell\\x08' contains the control character '\\x08'" in str(refusal.value)
    assert REMEDY in str(refusal.value)
