"""`--allow-errors` tolerates an existing parser diagnostic that is not a syntax error (w5/200).

Upstream reports two different things from the parser. A `ParserSyntaxError`
or `LexerError` is text it could not read. A `ParserError` is what a grammar
action says about text it did read: an option it does not know, a metadata key
given twice, a tag popped that was never pushed. The second kind was classed
with the first, so a ledger carrying one could not be written to at all — the
flag was refused with only the old error to show for it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from bea_engine.ledger import write as ledger_write
from bea_engine.query import readable_parser_message

ROOT = Path(__file__).resolve().parents[1]

BODY = """option "operating_currency" "USD"
{directive}
2026-01-01 open Assets:Cash USD
2026-01-01 open Equity:Opening

2026-01-02 * "Open"
{metadata}  Assets:Cash  100.00 USD
  Equity:Opening
{tail}"""

INVALID_OPTION = BODY.format(directive='option "experiment_explicit_tolerances" "TRUE"', metadata="", tail="")

# (ledger body, the existing diagnostic)
DIAGNOSTICS = [
    pytest.param(INVALID_OPTION, "main.bean:2: Invalid option: 'experiment_explicit_tolerances'", id="invalid-option"),
    pytest.param(
        BODY.format(directive="", metadata='  memo: "a"\n  memo: "b"\n', tail=""),
        "main.bean:6: Duplicate metadata field on entry: KeyValue(key='memo', value='b')",
        id="duplicate-metadata",
    ),
    pytest.param(
        BODY.format(directive="poptag #trip", metadata="", tail=""),
        "main.bean:2: Attempting to pop absent tag: 'trip'",
        id="absent-poptag",
    ),
]

# Still reported, but no longer an append target: an entry written after an
# open push inherits it, so the write refuses even under `--allow-errors`
# (w5/464; see test_append_after_open_push.py).
UNBALANCED_PUSHTAG = BODY.format(directive="pushtag #trip", metadata="", tail="")

# (ledger body, the error that still refuses every write)
SYNTAX_ERRORS = [
    pytest.param(
        BODY.format(directive="", metadata="", tail="2026-01-03 bogus Assets:Cash\n"),
        "main.bean:9: Invalid token: 'bogus'",
        id="grammar",
    ),
    pytest.param(
        BODY.format(directive="", metadata="", tail="2026-13-45 open Assets:Other\n"),
        "main.bean:9: ValueError: month must be in 1..12",
        id="lexer",
    ),
]

NOTE = ["add", "note", "--date", "2026-02-01", "-a", "Assets:Cash", "-m", "hi", "--allow-errors"]
WRITES = [
    pytest.param(NOTE, '2026-02-01 note Assets:Cash "hi"', id="note"),
    pytest.param(
        ["add", "price", "--date", "2026-02-01", "--commodity", "EUR", "--amount", "1.10 USD", "--allow-errors"],
        "2026-02-01 price EUR",
        id="price",
    ),
    pytest.param(
        [
            *["add", "transaction", "Lunch", "--date", "2026-02-01", "--allow-errors"],
            *["--posting", "Assets:Cash -5.00 USD", "--posting", "Equity:Opening"],
        ],
        '2026-02-01 * "Lunch"',
        id="transaction",
    ),
]


def _bea(tmp_path: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
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
        timeout=120,
    )


def _ledger(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(body, encoding="utf-8")
    return path


@pytest.mark.parametrize(("body", "diagnostic"), DIAGNOSTICS)
def test_an_existing_parser_diagnostic_stays_a_warning(tmp_path: Path, body: str, diagnostic: str) -> None:
    ledger = _ledger(tmp_path, body)
    checked = _bea(tmp_path, "--file", str(ledger), "check")
    assert checked.returncode == 1
    assert diagnostic in checked.stderr

    refused = _bea(tmp_path, "--file", str(ledger), *NOTE[:-1])
    assert refused.returncode == 1
    assert ledger.read_text() == body

    done = _bea(tmp_path, "--file", str(ledger), *NOTE)

    assert done.returncode == 0, done.stderr
    # Native `check` prints upstream's text; bea's own warning names the
    # value as ledger text, not a grammar repr (w5/334).
    location, _, message = diagnostic.partition(": ")
    assert f"{location}: {readable_parser_message(message)}" in done.stderr
    assert "nothing was written" not in done.stderr
    assert ledger.read_text().startswith(body)
    assert '2026-02-01 note Assets:Cash "hi"' in ledger.read_text()[len(body) :]


def test_an_unbalanced_pushtag_is_reported_and_refuses_an_append(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, UNBALANCED_PUSHTAG)
    checked = _bea(tmp_path, "--file", str(ledger), "check")
    assert checked.returncode == 1
    assert "Unbalanced pushed tag: 'trip'" in checked.stderr

    refused = _bea(tmp_path, "--file", str(ledger), *NOTE)
    assert refused.returncode == 2, refused.stderr
    assert "`pushtag #trip` at line 2" in refused.stderr
    assert ledger.read_text() == UNBALANCED_PUSHTAG


@pytest.mark.parametrize(("command", "written"), WRITES)
def test_every_add_form_tolerates_the_invalid_option(tmp_path: Path, command: list[str], written: str) -> None:
    ledger = _ledger(tmp_path, INVALID_OPTION)

    done = _bea(tmp_path, "--file", str(ledger), *command)

    assert done.returncode == 0, done.stderr
    assert "main.bean:2: Invalid option: 'experiment_explicit_tolerances'" in done.stderr
    assert written in ledger.read_text()[len(INVALID_OPTION) :]


def test_the_bulk_form_tolerates_the_invalid_option(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, INVALID_OPTION)
    rows = [
        {
            "date": "2026-02-01",
            "narration": "Lunch",
            "postings": [
                {"account": "Assets:Cash", "units": {"number": "-5.00", "currency": "USD"}},
                {"account": "Equity:Opening"},
            ],
        }
    ]

    done = _bea(
        tmp_path, "--file", str(ledger), "add", "transactions", "--from", "-", "--allow-errors", stdin=json.dumps(rows)
    )

    assert done.returncode == 0, done.stderr
    assert "Invalid option: 'experiment_explicit_tolerances'" in done.stderr
    assert '2026-02-01 * "Lunch"' in ledger.read_text()[len(INVALID_OPTION) :]


def test_a_failing_balance_is_the_unchanged_control(tmp_path: Path) -> None:
    body = BODY.format(directive="", metadata="", tail="2026-01-03 balance Assets:Cash 5 USD\n")
    ledger = _ledger(tmp_path, body)

    done = _bea(tmp_path, "--file", str(ledger), *NOTE)

    assert done.returncode == 0, done.stderr
    assert "main.bean:9: Balance failed for 'Assets:Cash'" in done.stderr
    assert '2026-02-01 note Assets:Cash "hi"' in ledger.read_text()[len(body) :]


@pytest.mark.parametrize(("body", "error"), SYNTAX_ERRORS)
def test_an_existing_syntax_error_is_still_refused(tmp_path: Path, body: str, error: str) -> None:
    ledger = _ledger(tmp_path, body)

    refused = _bea(tmp_path, "--file", str(ledger), *NOTE)

    assert refused.returncode == 1
    assert "The change would leave the ledger invalid; nothing was written." in refused.stderr
    assert error in refused.stderr
    assert ledger.read_text() == body


def test_a_parser_diagnostic_the_write_introduces_is_still_refused(tmp_path: Path) -> None:
    """Only the new diagnostic blocks; the one already in the books is not named."""
    ledger = _ledger(tmp_path, INVALID_OPTION)

    with pytest.raises(ledger_write.CandidateRejected) as refused:
        ledger_write.append(ledger, ["poptag #absent"], allow_errors=True, one_entry_each=False)

    assert str(refused.value) == "The change would introduce 1 new ledger error(s); nothing was written."
    assert len(refused.value.details) == 1
    assert "Attempting to pop absent tag: 'absent'" in refused.value.details[0]
    assert ledger.read_text() == INVALID_OPTION
