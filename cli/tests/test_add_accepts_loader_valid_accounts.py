"""`add` accepts every account name the loader does (w5/203).

An account whose name holds a character that is neither a letter nor a digit
— a Thai tone mark, a combining grave with no precomposed letter, a zero-width
space, an emoji — loads in stock Beancount, passes `bea check` and shows in
reports. `bea add` refused to post to it: its validator used Beancount's
end-anchored account pattern, while the loader takes anything its lexer reads
as one account token and only matches that pattern from the start.

The validator now asks the loader. A name the loader itself cannot read — a
lowercase root, a space, punctuation — is still a usage error, and so is a
control character or bidirectional override, which no write may carry.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

THAI = "Expenses:Kค่า"
LOADER_VALID = {
    "thai-tone-mark": THAI,
    "combining-grave": "Expenses:Ọ̀san",
    "zero-width-space": "Expenses:K​x",
    "emoji": "Expenses:K\U0001f600",
}

CSV = "Date,Amount,Description\n2026-02-01,-1.00,a\n2026-02-02,-2.00,b\n"


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    opens = "".join(f"2024-01-01 open {name} USD\n" for name in LOADER_VALID.values())
    path = tmp_path / "main.bean"
    path.write_text(
        'option "operating_currency" "USD"\n2024-01-01 open Assets:Bank USD\n2024-01-01 open Expenses:Rent USD\n'
        f'{opens}2024-01-02 * "rent"\n  {THAI}  5.00 USD\n  Assets:Bank\n',
        encoding="utf-8",
    )
    return path


def _bea(ledger: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    tmp_path = ledger.parent
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
        [sys.executable, "-m", "cli.main", "--no-input", "--file", str(ledger), *args],
        env=env,
        cwd=tmp_path,
        input=stdin,
        stdin=None if stdin is not None else subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )


def _transaction(ledger: Path, posting: str) -> subprocess.CompletedProcess[str]:
    return _bea(ledger, "add", "transaction", "--date", "2024-02-01", "-n", "rent", "-p", posting, "-p", "Assets:Bank")


def _assert_checks(ledger: Path) -> None:
    checked = _bea(ledger, "check")
    assert checked.returncode == 0, checked.stdout + checked.stderr


def test_the_fixture_ledger_is_one_check_accepts(ledger: Path) -> None:
    _assert_checks(ledger)


@pytest.mark.parametrize("name", LOADER_VALID.values(), ids=LOADER_VALID.keys())
def test_an_account_the_ledger_opens_can_be_posted_to(ledger: Path, name: str) -> None:
    added = _transaction(ledger, f"{name} 7 USD")

    assert added.returncode == 0, added.stderr
    assert f"\n  {name}  7 USD\n" in ledger.read_text(encoding="utf-8")
    _assert_checks(ledger)


@pytest.mark.parametrize(
    "args",
    [
        ("note", "--date", "2024-02-01", "-a", THAI, "-m", "hello"),
        ("balance", "--date", "2024-03-01", "-a", THAI, "--amount", "5 USD"),
        ("balance", "--date", "2024-03-02", "-a", "Assets:Bank", "--amount", "0 USD", "--pad-from", THAI),
        ("document", "--date", "2024-02-01", "-a", THAI, "--path", "receipt.pdf"),
        ("custom", "--date", "2024-02-01", "-t", "budget", "-v", f"account:{THAI}"),
        ("close", "--date", "2025-01-01", "-a", THAI),
    ],
    ids=["note", "balance", "pad-from", "document", "custom", "close"],
)
def test_every_account_taking_subcommand_accepts_it(ledger: Path, args: tuple[str, ...]) -> None:
    (ledger.parent / "receipt.pdf").write_bytes(b"%PDF-1.4\n")

    added = _bea(ledger, "add", *args)

    assert "Invalid account" not in added.stderr
    assert added.returncode == 0, added.stderr
    assert THAI in ledger.read_text(encoding="utf-8").split('"rent"', 1)[1].split("Assets:Bank\n", 1)[1]


def test_a_bulk_row_can_post_to_it(ledger: Path) -> None:
    rows = [{"date": "2024-02-03", "postings": [{"account": THAI, "amount": "3 USD"}, {"account": "Assets:Bank"}]}]

    added = _bea(ledger, "add", "transactions", "--from", "-", stdin=json.dumps(rows))

    assert added.returncode == 0, added.stderr
    assert ledger.read_text(encoding="utf-8").count(THAI) == 3
    _assert_checks(ledger)


def test_import_account_options_accept_it(ledger: Path) -> None:
    """The import options share the validator, and so did the refusal."""
    source = ledger.parent / "bank.csv"
    source.write_text(CSV, encoding="utf-8")

    preview = _bea(
        ledger, "import", str(source), "--csv", "auto", "--account", "Assets:Bank", "--default-account", THAI
    )

    assert preview.returncode == 0, preview.stderr
    assert "Invalid account" not in preview.stderr
    assert "blocked" not in preview.stdout


def test_a_new_account_with_a_combining_mark_can_be_opened(ledger: Path) -> None:
    """The unknown-account remedy names `add open`; it has to work for the same names."""
    name = "Expenses:Kx่y"
    unknown = _transaction(ledger, f"{name} 7 USD")
    assert unknown.returncode == 1, unknown.stdout
    assert "unknown account" in unknown.stderr
    assert "bea add open" in unknown.stderr

    opened = _bea(ledger, "add", "open", "--date", "2024-01-15", "-a", name)

    assert opened.returncode == 0, opened.stderr
    assert _transaction(ledger, f"{name} 7 USD").returncode == 0
    _assert_checks(ledger)


def test_an_ordinary_account_is_still_accepted(ledger: Path) -> None:
    """The control."""
    added = _transaction(ledger, "Expenses:Rent 7 USD")

    assert added.returncode == 0, added.stderr
    _assert_checks(ledger)


@pytest.mark.parametrize(
    ("name", "named"),
    [
        ("expenses:food", None),
        ("Expenses:food", None),
        ("Expenses", None),
        ("Expenses:่x", None),
        ("Expenses:Fo od", "U+0020 (SPACE)"),
        ("Expenses:Fo_od", "U+005F (LOW LINE)"),
        ("Expenses:K‮x", "U+202E (RIGHT-TO-LEFT OVERRIDE)"),
        ("Expenses:K\u0085x", "U+0085"),
    ],
    ids=["lowercase-root", "lowercase-segment", "root-only", "mark-first", "space", "underscore", "bidi", "c1"],
)
def test_a_name_the_loader_cannot_read_is_still_refused(ledger: Path, name: str, named: str | None) -> None:
    before = ledger.read_bytes()

    refused = _bea(ledger, "add", "note", "--date", "2024-02-01", "-a", name, "-m", "hello")

    assert refused.returncode == 2, refused.stdout
    assert "Invalid account" in refused.stderr
    if named is None:
        assert "The character" not in refused.stderr
    else:
        assert f"The character {named} is not allowed." in " ".join(refused.stderr.split())
    assert ledger.read_bytes() == before


def test_a_malformed_posting_account_is_still_refused(ledger: Path) -> None:
    before = ledger.read_bytes()

    refused = _transaction(ledger, "expenses:food 7 USD")

    assert refused.returncode == 2, refused.stdout
    assert "Invalid account 'expenses:food'" in refused.stderr
    assert ledger.read_bytes() == before
