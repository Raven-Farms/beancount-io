"""Repeated `--tag`/`--link` require every value, and the advice and docs say so (w5/835).

`--tag trip,work` was refused with "Repeat --tag for several tags"; following
it found nothing, exit 0, because repeats are ANDed, which only `--search`
documented.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
LEDGER = (
    "2026-01-01 open Assets:Cash USD\n2026-01-01 open Expenses:Food USD\n"
    '2026-02-01 * "A" #trip ^a\n  Expenses:Food  1 USD\n  Assets:Cash\n'
    '2026-02-02 * "B" #work ^b\n  Expenses:Food  1 USD\n  Assets:Cash\n'
    '2026-02-03 * "C" #trip #work ^a ^b\n  Expenses:Food  1 USD\n  Assets:Cash\n'
)


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(LEDGER)
    return path


@pytest.mark.parametrize(("flag", "values"), [("--tag", ("trip", "work")), ("--link", ("a", "b"))])
def test_the_advice_describes_and_and_repeats_require_every_value(
    ledger: Path, flag: str, values: tuple[str, str]
) -> None:
    refused = runner.invoke(app, ["--file", str(ledger), "list", "transaction", flag, ",".join(values)])

    assert refused.exit_code == 2, refused.output
    noun = "tags" if flag == "--tag" else "links"
    assert f"Repeat {flag} to require several {noun} on one transaction." in " ".join(refused.stderr.split())

    both = runner.invoke(
        app, ["--json", "--file", str(ledger), "list", "transaction", flag, values[0], flag, values[1]]
    )
    assert [row["narration"] for row in json.loads(both.stdout)["data"]] == ["C"]


def test_help_and_usage_say_and(ledger: Path) -> None:
    help_text = " ".join(runner.invoke(app, ["list", "transaction", "--help"]).output.split())
    usage = (Path(__file__).resolve().parents[1] / "docs" / "USAGE.md").read_text()

    assert "repeat to require every tag" in help_text and "case-sensitive" in help_text
    assert "Repeatable (AND — a row must carry every tag given)" in usage
