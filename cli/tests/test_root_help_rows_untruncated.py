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


def _group_rows(path: list[str], width: int) -> dict[str, str]:
    """Each subcommand's summary on a group page, keyed by name (w5/752).

    The root list was shortened in w5/264, but thirteen sub-group rows still
    overran their row and printed with `...`, and the `import --csv` example
    split `narration=Description` mid-word at every width.
    """
    result = runner.invoke(app, [*path, "--help"], env={"COLUMNS": str(width)})
    assert result.exit_code == 0, result.output
    rows: dict[str, str] = {}
    in_panel = False
    for line in result.stdout.splitlines():
        if not line.startswith(" "):
            in_panel = line.endswith(":") and not line.startswith(("Usage", "Options"))
        elif in_panel and line.strip():
            name, _, summary = line.strip().partition(" ")
            rows[name] = summary.strip()
    return rows


SUBGROUPS: dict[tuple[str, ...], set[str]] = {
    ("list",): {"transaction"},
    ("report",): {"income-statement", "balance-sheet", "trial-balance"},
    ("add",): {"close", "balance", "price"},
    ("engine",): {"status", "enable"},
    ("cloud",): {"login", "status"},
    ("cloud", "ledger"): {"list"},
    ("ingest",): {"identify", "extract"},
}


@pytest.mark.parametrize(("path", "members"), [(list(p), m) for p, m in SUBGROUPS.items()])
@pytest.mark.parametrize("width", [80, 200])
def test_no_subgroup_summary_is_cut_short(path: list[str], members: set[str], width: int) -> None:
    rows = _group_rows(path, width)

    # The rows being read are the real ones, or the check below proves nothing.
    assert members <= set(rows)
    assert {name: summary for name, summary in rows.items() if summary.endswith("...")} == {}


@pytest.mark.parametrize(
    ("path", "command", "summary"),
    [
        (["list"], "transaction", "List recent transactions and their amounts."),
        (["report"], "income-statement", "Income, expenses, and profit by interval."),
        (["report"], "balance-sheet", "Assets, liabilities, and equity."),
        (["report"], "trial-balance", "All five account types, with signed balances."),
        (["add"], "close", "Append a close directive."),
        (["add"], "balance", "Append a balance assertion, or pad from another account."),
        (["add"], "price", "Append a price directive."),
        (["engine"], "status", "Show which engine serves local commands."),
        (["engine"], "enable", "Install a reviewed optional package."),
        (["cloud"], "login", "Log in by device flow."),
        (["cloud"], "status", "Show the current login."),
        (["cloud", "ledger"], "list", "List accessible ledgers."),
        (["ingest"], "identify", "Identify which importer matches each document."),
        (["ingest"], "extract", "Extract raw entries from documents."),
    ],
)
def test_the_shortened_subgroup_summaries_print_whole(path: list[str], command: str, summary: str) -> None:
    assert _group_rows(path, 80)[command] == summary


@pytest.mark.parametrize(
    ("path", "detail"),
    [
        (["report", "balance-sheet"], "Includes current earnings and valuation adjustments."),
        (["add", "price"], "An exact ledger-authored date/commodity/amount match is reported"),
        (["engine", "status"], "which optional features are enabled"),
        (["engine", "enable"], "never into the bea frontend"),
        (["cloud", "login"], "$BEA_CONFIG_DIR, $XDG_CONFIG_HOME/bea or ~/.config/bea"),
        (["cloud", "status"], "where the credential came from, and when it expires"),
        (["cloud", "ledger", "list"], "restricted to the credential's ledger pin when present"),
        (["ingest", "extract"], "This is not bea import --apply."),
    ],
)
def test_the_detail_that_left_the_row_survives_in_the_body(path: list[str], detail: str) -> None:
    # Shortening a row must move its meaning down the page, never delete it.
    # Whitespace is collapsed first: line wraps are rendering, not content.
    result = runner.invoke(app, [*path, "--help"])

    assert result.exit_code == 0
    assert detail in " ".join(result.stdout.split())


@pytest.mark.parametrize("width", [80, 200])
def test_the_csv_example_never_splits_a_field_mid_word(width: int) -> None:
    # The mapping example is one 52-character token without spaces, so click
    # could only wrap it mid-word; spaces after the commas give it breakpoints.
    # (At widths narrower than the token itself no breakpoint can help.)
    result = runner.invoke(app, ["import", "--help"], env={"COLUMNS": str(width)})

    assert result.exit_code == 0
    assert any("narration=Description" in line for line in result.stdout.splitlines())
