"""`bea --help` prints every command's summary whole (w5/264).

click cuts a summary that overruns the row at a word boundary and appends
`...`. The root list is the first thing a newcomer reads, and five commands
added after the summaries were first shortened had grown past the limit again.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()


def _command_rows(width: int) -> dict[str, str]:
    """Each root command's summary, keyed by name, as `--help` renders it."""
    # COLUMNS is what a terminal of that size reports; click caps the page at 80.
    result = runner.invoke(app, ["--help"], env={"COLUMNS": str(width)})
    assert result.exit_code == 0, result.output
    rows: dict[str, str] = {}
    in_panel = False
    for line in result.stdout.splitlines():
        if not line.startswith(" "):
            # Panel titles name the commands' home; `Options:` rows are not commands.
            in_panel = line.endswith(":") and not line.startswith(("Usage", "Options"))
        elif in_panel and line.strip():
            name, _, summary = line.strip().partition(" ")
            rows[name] = summary.strip()
    return rows


@pytest.mark.parametrize("width", [80, 200])
def test_no_root_command_summary_is_cut_short(width: int) -> None:
    rows = _command_rows(width)

    # The rows being read are the real ones, or the check below proves nothing.
    assert {"check", "price", "example", "treeify", "ingest", "engine", "cloud"} <= set(rows)
    assert {name: summary for name, summary in rows.items() if summary.endswith("...")} == {}


@pytest.mark.parametrize(
    ("command", "summary"),
    [
        ("price", "Inspect managed price includes, or fetch bean-price quotes."),
        ("example", "Generate an example ledger (delegates to bean-example)."),
        ("treeify", "Render a column as an ASCII tree (delegates to treeify)."),
        ("ingest", "Run Beangulp identify/extract/archive via your ingest script."),
        ("engine", "Manage the Beancount engine and its optional features."),
    ],
)
def test_the_summaries_that_regressed_print_whole(command: str, summary: str) -> None:
    assert _command_rows(80)[command] == summary


def test_the_summaries_first_shortened_still_print_whole() -> None:
    rows = _command_rows(80)

    assert rows["init"] == "Create main.bean with common accounts."
    assert rows["import"] == "Preview bank-export entries; write with --apply."
    assert rows["query"] == "Run BQL queries against a local ledger."
    assert rows["ask"] == "Ask about a local ledger via hosted AI."
    assert rows["cloud"] == "Hosted ledgers and AI proxy; see 'cloud login'."


def test_ingest_help_still_names_its_engine_feature() -> None:
    # The prerequisite moved out of the summary into the body; it must not vanish.
    result = runner.invoke(app, ["ingest", "--help"])

    assert result.exit_code == 0
    assert "Requires 'bea engine enable beangulp'." in result.stdout
