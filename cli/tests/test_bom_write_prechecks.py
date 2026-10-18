"""Write prechecks see first-line BOM directives and the loader's normalized roots (w5/710)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BOM = b"\xef\xbb\xbf"
MAIN = (
    'include "inc.bean"\n'
    "2026-01-01 open Assets:Cash USD\n"
    "2026-01-01 open Expenses:Food USD\n"
    "2026-01-01 open Equity:Opening USD\n"
)
ENTRY = '2026-01-02 * "Existing"\n  Assets:Cash 1 USD\n  Equity:Opening\n'
PUSHES = {
    "tag": ("pushtag #trip\n", "poptag #trip\n", "pushtag #trip"),
    "metadata": ('pushmeta source: "bank-a"\n', "popmeta source:\n", "pushmeta source:"),
}


def _env(directory: Path) -> dict[str, str]:
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
    return env


def _bea(root: Path, *args: str, as_json: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "cli.main",
            *(["--json"] if as_json else []),
            "--no-input",
            "--file",
            str(root),
            *args,
        ],
        cwd=root.parent,
        env=_env(root.parent),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _success(done: subprocess.CompletedProcess[str]) -> None:
    assert done.returncode == 0, done.stdout + done.stderr


def _push_books(directory: Path, push: str, *, bom: bool = True, closed: bool = False) -> tuple[Path, Path]:
    root = directory / "main.bean"
    member = directory / "inc.bean"
    root.write_text(MAIN)
    start, stop, _ = PUSHES[push]
    member.write_bytes((BOM if bom else b"") + (start + ENTRY + (stop if closed else "")).encode())
    return root, member


def _write_args(root: Path, operation: str) -> list[str]:
    if operation == "transaction":
        return [
            "add",
            "transaction",
            "Written",
            "--date",
            "2026-01-05",
            "-p",
            "Expenses:Food 3 USD",
            "-p",
            "Assets:Cash",
        ]
    if operation == "note":
        return ["add", "note", "--date", "2026-01-05", "-a", "Assets:Cash", "-m", "Written"]
    if operation == "bulk":
        source = root.parent / "rows.json"
        source.write_text(
            json.dumps(
                [
                    {
                        "date": "2026-01-05",
                        "narration": "Written",
                        "postings": [{"account": "Expenses:Food", "amount": "3 USD"}, {"account": "Assets:Cash"}],
                    }
                ]
            )
        )
        return ["add", "transactions", "--from", str(source)]
    assert operation == "import"
    source = root.parent / "statement.csv"
    source.write_text("Date,Description,Amount\n2026-01-05,Written,-3.00\n")
    return [
        "import",
        str(source),
        "--csv",
        "date=Date,narration=Description,amount=Amount",
        "--account",
        "Assets:Cash",
        "--default-account",
        "Expenses:Food",
        "--apply",
    ]


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
@pytest.mark.parametrize("push", PUSHES)
@pytest.mark.parametrize("operation", ["transaction", "note", "bulk", "import"])
def test_first_line_bom_push_refuses_every_append_even_with_allow_errors(
    tmp_path: Path, operation: str, push: str, as_json: bool
) -> None:
    root, member = _push_books(tmp_path, push)
    before = {path: path.read_bytes() for path in (root, member)}

    done = _bea(root, *_write_args(root, operation), "--into", member.name, "--allow-errors", as_json=as_json)

    assert done.returncode == 2, done.stdout + done.stderr
    assert done.stdout == ""
    if as_json:
        error = json.loads(done.stderr)["error"]
        assert error["category"] == "usage" and error["exit_code"] == 2
        message = error["message"]
    else:
        message = " ".join(done.stderr.split())
    assert str(member) in message
    assert f"`{PUSHES[push][2]}` at line 1" in message
    assert "silently inherit" in message and "Close it first" in message
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize("push", PUSHES)
def test_raw_append_has_the_same_bom_push_guard(tmp_path: Path, push: str) -> None:
    root, member = _push_books(tmp_path, push)
    before = {path: path.read_bytes() for path in (root, member)}

    done = subprocess.run(
        [
            sys.executable,
            "-m",
            "bea_engine",
            "append",
            "--file",
            str(root),
            "--into",
            member.name,
            "--allow-errors",
            "--text",
            '2026-01-05 note Assets:Cash "Written"\n',
        ],
        cwd=tmp_path,
        env=_env(tmp_path),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert done.returncode == 2, done.stdout + done.stderr
    error = json.loads(done.stdout)["error"]
    assert error["category"] == "usage"
    assert f"`{PUSHES[push][2]}` at line 1" in error["message"]
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize("push", PUSHES)
def test_closed_bom_push_allows_a_write_without_inheriting_tag_or_metadata(tmp_path: Path, push: str) -> None:
    root, member = _push_books(tmp_path, push, closed=True)
    before = member.read_bytes()
    root_before = root.read_bytes()

    _success(_bea(root, *_write_args(root, "note"), "--into", member.name))

    assert member.read_bytes().startswith(before)
    assert member.read_bytes().startswith(BOM)
    assert root.read_bytes() == root_before
    _success(_bea(root, "check"))
    listed = _bea(root, "list", "note")
    _success(listed)
    (note,) = json.loads(listed.stdout)["data"]
    assert note["comment"] == "Written" and note["tags"] == [] and note["meta"] == {}


@pytest.mark.parametrize("push", PUSHES)
def test_the_existing_no_bom_open_push_refusal_is_unchanged(tmp_path: Path, push: str) -> None:
    root, member = _push_books(tmp_path, push, bom=False)
    before = member.read_bytes()

    refused = _bea(root, *_write_args(root, "note"), "--into", member.name, "--allow-errors")

    assert refused.returncode == 2, refused.stdout + refused.stderr
    assert f"`{PUSHES[push][2]}` at line 1" in json.loads(refused.stderr)["error"]["message"]
    assert member.read_bytes() == before


def _root_books(directory: Path, root_name: str, *, bom: bool, option_name: str | None = None) -> Path:
    root = directory / "main.bean"
    text = (
        f'option "name_assets" "{option_name or root_name}"\n'
        f"2026-01-01 open {root_name}:Cash USD\n"
        "2026-01-01 open Equity:Opening USD\n"
    )
    root.write_bytes((BOM if bom else b"") + text.encode())
    (directory / "receipt.pdf").write_bytes(b"%PDF-1.4\n")
    return root


def _simple_args(operation: str, account: str) -> list[str]:
    base = ["add", operation, "--date", "2026-01-05", "--account", account]
    if operation == "open":
        return [*base[:-1], account.rsplit(":", 1)[0] + ":New", "--currency", "USD"]
    if operation == "note":
        return [*base, "--comment", "Written"]
    if operation == "document":
        return [*base, "--filename", "receipt.pdf"]
    if operation == "pad":
        return [*base, "--source", "Equity:Opening", "--allow-errors"]
    assert operation == "close"
    return base


def _write_and_check_simple(root: Path, operation: str, account: str, *, as_json: bool) -> None:
    original = root.read_bytes()
    _success(_bea(root, "check"))

    _success(_bea(root, *_simple_args(operation, account), as_json=as_json))

    written = root.read_bytes()
    assert written.startswith(original)
    expected = unicodedata.normalize("NFC", account)
    if operation == "open":
        expected = expected.rsplit(":", 1)[0] + ":New"
    assert f"2026-01-05 {operation} {expected}" in written[len(original) :].decode()
    if operation == "pad":
        # Complete the documented staged-pad flow so the written root semantics
        # are checked too, rather than merely tolerating its temporary error.
        _success(_bea(root, "add", "balance", "--date", "2026-01-06", "-a", account, "--amount", "1 USD"))
    _success(_bea(root, "check"))


@pytest.mark.parametrize("operation", ["open", "note", "close", "pad", "document"])
def test_simple_writes_use_a_first_line_bom_root_option(tmp_path: Path, operation: str) -> None:
    root = _root_books(tmp_path, "Activos", bom=True)

    _write_and_check_simple(root, operation, "Activos:Cash", as_json=operation in {"open", "close", "document"})

    assert root.read_bytes().startswith(BOM)


@pytest.mark.parametrize("input_form", ["NFC", "NFD"])
@pytest.mark.parametrize("operation", ["open", "note", "close", "pad", "document"])
def test_nfd_root_options_accept_both_normalized_account_spellings(
    tmp_path: Path, operation: str, input_form: str
) -> None:
    name = "Vermögen"
    root = _root_books(tmp_path, name, bom=False, option_name=unicodedata.normalize("NFD", name))
    account = unicodedata.normalize(input_form, name + ":Cash")

    _write_and_check_simple(root, operation, account, as_json=input_form == "NFD")


@pytest.mark.parametrize("prior", [None, "Activos"], ids=["retain-default", "retain-prior-valid"])
def test_an_invalid_last_root_option_does_not_replace_the_loaders_previous_root(
    tmp_path: Path, prior: str | None
) -> None:
    name = prior or "Assets"
    text = (f'option "name_assets" "{prior}"\n' if prior else "") + 'option "name_assets" "invalid"\n'
    text += f"2026-01-01 open {name}:Cash USD\n"
    root = tmp_path / "main.bean"
    root.write_text(text)
    before = root.read_bytes()

    added = _bea(root, "add", "note", "--date", "2026-01-05", "-a", f"{name}:Cash", "-m", "Written", "--allow-errors")

    _success(added)
    assert root.read_bytes().startswith(before)
    assert f'2026-01-05 note {name}:Cash "Written"' in root.read_text()
    checked = _bea(root, "check")
    assert checked.returncode == 1, checked.stdout + checked.stderr
    assert "Invalid root account name" in checked.stderr
    assert any("Invalid root account name" in warning for warning in json.loads(added.stdout)["data"]["warnings"])


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_a_new_glob_member_is_seeded_from_the_bom_first_root_option_and_checks(tmp_path: Path, as_json: bool) -> None:
    root = tmp_path / "main.bean"
    original = BOM + (
        b'option "name_assets" "Activos"\noption "name_expenses" "Aufwand"\n'
        b'include "txns/*.bean"\n'
        b"2026-01-01 open Activos:Cash USD\n2026-01-01 open Aufwand:Food USD\n"
    )
    root.write_bytes(original)
    (tmp_path / "txns").mkdir()
    (tmp_path / "txns" / "old.bean").write_text("")
    _success(_bea(root, "check"))

    _success(
        _bea(
            root,
            "add",
            "transaction",
            "Written",
            "--date",
            "2026-01-05",
            "-p",
            "Aufwand:Food 3 USD",
            "-p",
            "Activos:Cash",
            "--into",
            "txns/new.bean",
            as_json=as_json,
        )
    )

    assert root.read_bytes() == original
    member = tmp_path / "txns" / "new.bean"
    assert member.read_text().startswith('option "name_assets" "Activos"\noption "name_expenses" "Aufwand"\n')
    _success(_bea(root, "check"))
    query = _bea(root, "query", "SELECT account, sum(position) GROUP BY account ORDER BY account")
    _success(query)
    rows = json.loads(query.stdout)["data"]["rows"]
    assert rows == [
        ["Activos:Cash", [{"units": {"number": "-3", "currency": "USD"}, "cost": None}]],
        ["Aufwand:Food", [{"units": {"number": "3", "currency": "USD"}, "cost": None}]],
    ]
