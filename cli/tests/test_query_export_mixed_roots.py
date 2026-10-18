"""Flattened Beancount exports preserve per-file roots and final root options (w5/685)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from beancount.core import account
from beancount.core.data import Custom, Note, Open
from beancount.parser import parser
from beancount.parser.options import OPTIONS_DEFAULTS

ROOT = Path(__file__).resolve().parents[1]
RENAMED = {
    "Assets": "Activos",
    "Liabilities": "Pasivos",
    "Equity": "Patrimonio",
    "Income": "Ingresos",
    "Expenses": "Gastos",
}
ROOT_OPTIONS = {name: f"name_{name.lower()}" for name in RENAMED}
SENTINEL = b"LAST GOOD EXPORT\n"


def _bea(directory: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_") and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    env.update(
        BEA_CONFIG_DIR=str(directory / "config"),
        XDG_CACHE_HOME=str(directory / "cache"),
        XDG_DATA_HOME=str(directory / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", *args],
        env=env,
        cwd=directory,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _books(tmp_path: Path, root_text: str, child_text: str = "") -> Path:
    root = tmp_path / "main.bean"
    root.write_text(root_text)
    (tmp_path / "inc.bean").write_text(child_text)
    return root


def _check(root: Path) -> None:
    checked = _bea(root.parent, "--file", str(root), "check")
    assert checked.returncode == 0, checked.stdout + checked.stderr


def _snapshot(root: Path) -> dict[Path, bytes]:
    return {path: path.read_bytes() for path in (root, root.with_name("inc.bean"))}


def _parse(text: str) -> tuple[list[Any], dict[str, Any]]:
    entries, errors, options = parser.parse_string(text)
    assert not errors, f"{errors}\n{text}"
    return entries, options


def _export(root: Path, statement: str = "PRINT", *, to_file: bool = False) -> str:
    destination = root.with_name("export.bean")
    result = _bea(
        root.parent,
        "--file",
        str(root),
        "query",
        "--format",
        "beancount",
        *(["--output", str(destination)] if to_file else []),
        statement,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    if to_file:
        assert result.stdout == ""
        return destination.read_text()
    return result.stdout


def _recheck_text(root: Path, text: str) -> None:
    exported = root.with_name("roundtrip.bean")
    exported.write_text(text)
    _check(exported)


@pytest.mark.parametrize("surface", ["stdout", "output-file", "stored-query"])
def test_the_reported_default_include_under_a_renamed_root_exports_and_rechecks(tmp_path: Path, surface: str) -> None:
    root_text = (
        'option "name_assets" "Activos"\ninclude "inc.bean"\n'
        "2026-01-01 open Activos:Cash USD\n2026-01-01 open Expenses:Food USD\n"
    )
    if surface == "stored-query":
        root_text += '2026-01-02 query "flat" "PRINT"\n'
    root = _books(tmp_path, root_text, "2026-01-01 open Assets:Bank USD\n")
    before = _snapshot(root)
    _check(root)

    text = _export(root, ".run flat" if surface == "stored-query" else "PRINT", to_file=surface == "output-file")

    _recheck_text(root, text)
    entries, options = _parse(text)
    assert {entry.account for entry in entries if isinstance(entry, Open)} == {
        "Assets:Bank",
        "Activos:Cash",
        "Expenses:Food",
    }
    assert options["name_assets"] == "Activos"
    assert _snapshot(root) == before


@pytest.mark.parametrize("kind", RENAMED)
def test_each_root_kind_can_switch_for_a_late_default_entry_and_restore_final_options(
    tmp_path: Path, kind: str
) -> None:
    renamed = RENAMED[kind]
    option = ROOT_OPTIONS[kind]
    counter = "Assets:Bridge" if kind == "Equity" else "Equity:Bridge"
    root = _books(
        tmp_path,
        f'option "{option}" "{renamed}"\ninclude "inc.bean"\n'
        f"2026-01-01 open {renamed}:Root USD\n2026-01-01 open {counter} USD\n"
        f'2026-01-02 * "renamed-first"\n  {renamed}:Root 1 USD\n  {counter} -1 USD\n',
        f"2026-01-01 open {kind}:Included USD\n"
        f'2026-01-03 * "default-last"\n  {kind}:Included 2 USD\n  {counter} -2 USD\n',
    )
    _check(root)
    before = _snapshot(root)

    text = _export(root, to_file=True)

    _recheck_text(root, text)
    assert text.index('"renamed-first"') < text.index('"default-last"'), text
    assert text.rfind(f'option "{option}" "{renamed}"') > text.index('"default-last"'), text
    _, options = _parse(text)
    for root_kind, root_option in ROOT_OPTIONS.items():
        assert options[root_option] == (renamed if root_kind == kind else OPTIONS_DEFAULTS[root_option])
    assert _snapshot(root) == before


def test_select_entry_keeps_requested_transaction_order_across_root_switches(tmp_path: Path) -> None:
    root = _books(
        tmp_path,
        'option "name_assets" "Activos"\ninclude "inc.bean"\n'
        "2026-01-01 open Activos:Cash USD\n2026-01-01 open Equity:Opening USD\n"
        '2026-01-02 * "z-renamed"\n  Activos:Cash 1 USD\n  Equity:Opening -1 USD\n',
        '2026-01-01 open Assets:Cash USD\n2026-01-02 * "a-default"\n  Assets:Cash 2 USD\n  Equity:Opening -2 USD\n',
    )
    _check(root)
    statement = "SELECT entry WHERE account ~ '(Assets|Activos):' ORDER BY narration DESC"

    text = _export(root, statement)

    assert text.index('"z-renamed"') < text.index('"a-default"'), text
    entries, options = _parse(text)
    assert len(entries) == 2 and options["name_assets"] == "Activos"
    assert sorted(posting.account for entry in entries for posting in entry.postings) == [
        "Activos:Cash",
        "Assets:Cash",
        "Equity:Opening",
        "Equity:Opening",
    ]


def test_custom_account_values_get_the_same_root_switches_as_directive_accounts(tmp_path: Path) -> None:
    root = _books(
        tmp_path,
        'option "name_assets" "Activos"\ninclude "inc.bean"\n'
        "2026-01-01 open Activos:Cash USD\n"
        '2026-01-02 custom "root-account" Activos:Cash\n',
        '2026-01-01 open Assets:Bank USD\n2026-01-03 custom "default-account" Assets:Bank\n',
    )
    _check(root)

    text = _export(root)

    _recheck_text(root, text)
    entries, options = _parse(text)
    values = {entry.type: entry.values[0] for entry in entries if isinstance(entry, Custom)}
    assert values["root-account"].value == "Activos:Cash" and values["root-account"].dtype == account.TYPE
    assert values["default-account"].value == "Assets:Bank" and values["default-account"].dtype == account.TYPE
    assert options["name_assets"] == "Activos"


@pytest.mark.parametrize("case", ["foreign-child-root", "child-only-rename"])
@pytest.mark.parametrize("destination", ["stdout", "file"])
def test_foreign_include_roots_refuse_before_any_output_without_guessing_their_category(
    tmp_path: Path, case: str, destination: str
) -> None:
    if case == "foreign-child-root":
        root_option, child_root = 'option "name_assets" "Activos"\n', "Foreign"
    else:
        root_option, child_root = "", "Activos"
    root = _books(
        tmp_path,
        root_option + 'include "inc.bean"\n',
        f'option "name_assets" "{child_root}"\n2026-01-01 open {child_root}:Bank USD\n',
    )
    _check(root)
    before = _snapshot(root)
    out = tmp_path / "refused.bean"
    for existing in [False, True] if destination == "file" else [False]:
        if existing:
            out.write_bytes(SENTINEL)
        result = _bea(
            tmp_path,
            "--file",
            str(root),
            "query",
            "--format",
            "beancount",
            *(["--output", str(out)] if destination == "file" else []),
            "PRINT",
        )
        assert result.returncode == 1, result.stdout + result.stderr
        assert result.stdout == ""
        assert f"{child_root}:Bank" in result.stderr and "Cannot export" in result.stderr
        assert "original split ledger" in result.stderr and "Traceback" not in result.stderr
        assert _snapshot(root) == before
        assert out.read_bytes() == SENTINEL if existing else not out.exists()


@pytest.mark.parametrize("kind", ["transaction", "custom-account-values"])
@pytest.mark.parametrize("destination", ["stdout", "file"])
def test_one_entry_requiring_both_names_for_the_same_root_kind_refuses_atomically(
    tmp_path: Path, kind: str, destination: str
) -> None:
    # The include can parse both names using two categories. The root's final
    # options put Activos in Assets; flattening must not borrow another category.
    entry = (
        '2026-01-02 * "both roots"\n  Assets:Cash 1 USD\n  Activos:Reserve -1 USD\n'
        if kind == "transaction"
        else '2026-01-02 custom "both roots" Assets:Cash Activos:Reserve\n'
    )
    root = _books(
        tmp_path,
        'option "name_assets" "Activos"\ninclude "inc.bean"\n',
        'option "name_liabilities" "Activos"\n'
        "2026-01-01 open Assets:Cash USD\n2026-01-01 open Activos:Reserve USD\n" + entry,
    )
    _check(root)
    before = _snapshot(root)
    out = tmp_path / "refused.bean"
    if destination == "file":
        out.write_bytes(SENTINEL)

    result = _bea(
        tmp_path,
        "--file",
        str(root),
        "query",
        "--format",
        "beancount",
        *(["--output", str(out)] if destination == "file" else []),
        "PRINT",
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stdout == ""
    assert "Assets:Cash" in result.stderr and "Activos:Reserve" in result.stderr, result.stderr
    assert "Cannot export" in result.stderr and "original split ledger" in result.stderr
    assert out.read_bytes() == SENTINEL if destination == "file" else not out.exists()
    assert _snapshot(root) == before


def test_account_looking_metadata_strings_do_not_require_or_conflict_with_root_switches(tmp_path: Path) -> None:
    root = _books(
        tmp_path,
        'option "name_assets" "Activos"\n2026-01-01 open Activos:Cash USD\n'
        '2026-01-02 note Activos:Cash "memo"\n'
        '  account-text: "Assets:Bank"\n  foreign-text: "Foreign:Memo"\n  plain-text: "just text"\n',
    )
    _check(root)

    text = _export(root)

    _recheck_text(root, text)
    entries, options = _parse(text)
    [note] = [entry for entry in entries if isinstance(entry, Note)]
    assert note.meta["account-text"] == "Assets:Bank"
    assert note.meta["foreign-text"] == "Foreign:Memo" and note.meta["plain-text"] == "just text"
    assert 'option "name_assets" "Assets"' not in text
    assert options["name_assets"] == "Activos"


def test_a_default_root_ledger_keeps_its_option_free_export(tmp_path: Path) -> None:
    root = _books(
        tmp_path,
        "2026-01-01 open Assets:Cash USD\n2026-01-01 open Equity:Opening USD\n"
        '2026-01-02 * "plain"\n  Assets:Cash 2 USD\n  Equity:Opening -2 USD\n',
    )
    _check(root)
    before = _snapshot(root)

    text = _export(root)

    assert text.startswith("2026-01-01 open Assets:Cash ") and "option " not in text
    _recheck_text(root, text)
    assert _snapshot(root) == before
