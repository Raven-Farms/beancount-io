"""Early import refusals retain only the settings provenance their mapping origin warrants (w5/715)."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAPPING = "date=Date,amount=Amount,narration=Description"
LEDGER = (
    'option "operating_currency" "EUR"\n'
    "2026-01-01 open Assets:Checking EUR\n"
    "2026-01-01 open Expenses:Uncategorized EUR\n"
)
REMEMBERED = "Using settings remembered from seed.csv for next.csv:"
INFERRED = "Read the column mapping from the header row:"
UNREADABLE = "Cannot read remembered import settings in"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(LEDGER)
    return path


def _source(
    root: Path,
    *,
    date: str = "2026-03-14",
    description: bytes = b"Coffee",
    amount: str = "-4.50",
    name: str = "next.csv",
) -> Path:
    source = root.parent / name
    source.write_bytes(
        b"Date,Description,Amount\n" + date.encode() + b"," + description + b"," + amount.encode() + b"\n"
    )
    return source


def _import(root: Path, source: Path, *args: str, as_json: bool = True) -> subprocess.CompletedProcess[str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_") and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    env.update(
        BEA_CONFIG_DIR=str(root.parent / "config"),
        XDG_CACHE_HOME=str(root.parent / "cache"),
        XDG_DATA_HOME=str(root.parent / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "cli.main",
            *(["--json"] if as_json else []),
            "--no-input",
            "--file",
            str(root),
            "import",
            str(source),
            *args,
        ],
        cwd=root.parent,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _seed(root: Path, *, encoding: str = "utf-8", date_format: str | None = None) -> None:
    source = _source(
        root,
        name="seed.csv",
        date="13/03/2026" if date_format else "2026-03-01",
        description="Café Crème".encode(encoding),
    )
    spec = MAPPING + (f",encoding={encoding}" if encoding != "utf-8" else "")
    done = _import(
        root,
        source,
        "--csv",
        spec,
        "--account",
        "Assets:Checking",
        *(["--date-format", date_format] if date_format else []),
        "--apply",
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert json.loads(done.stdout)["data"]["written"] == 1


def _snapshot(root: Path) -> dict[Path, bytes]:
    files = [root, *root.parent.glob("*.csv"), *(root.parent / "config" / "importers").glob("*.json")]
    return {path: path.read_bytes() for path in files}


def _error(done: subprocess.CompletedProcess[str], *, as_json: bool) -> tuple[dict[str, Any], str]:
    assert done.returncode == 2, done.stdout + done.stderr
    assert done.stdout == ""
    if as_json:
        error = dict(json.loads(done.stderr)["error"])
        assert error["category"] == "usage" and error["exit_code"] == 2
        assert "result" not in error
        return error, "\n".join([str(error["message"]), *error.get("details", [])])
    return {}, " ".join(done.stderr.split())


def _notes_first(error: dict[str, Any], text: str, prefix: str, *, as_json: bool) -> None:
    if as_json:
        assert error["details"][0].startswith(prefix)
    assert text.count(prefix) == 1, text


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
@pytest.mark.parametrize("apply", [False, True], ids=["preview", "apply"])
@pytest.mark.parametrize("case", ["remembered-date", "remembered-codec", "unreadable-memory", "typed-date"])
def test_the_four_early_refusals_preserve_their_settings_origin_and_files(
    root: Path, case: str, apply: bool, as_json: bool
) -> None:
    flags: list[str] = []
    if case == "remembered-date":
        _seed(root, date_format="%d/%m/%Y")
        source = _source(root)
    elif case == "remembered-codec":
        _seed(root, encoding="cp1252")
        source = _source(root, description=b"Bad\x81")
    elif case == "unreadable-memory":
        if os.name != "posix" or os.geteuid() == 0:
            pytest.skip("requires POSIX directory permissions enforced for the current user")
        _seed(root, encoding="cp1252")
        source = _source(root, description="Café".encode("cp1252"))
    else:
        source = _source(root, date="2026-03-99")
        flags = ["--csv", MAPPING, "--account", "Assets:Checking"]
    before = _snapshot(root)
    memory = root.parent / "config" / "importers"
    mode = stat.S_IMODE(memory.stat().st_mode) if case == "unreadable-memory" else None
    try:
        if mode is not None:
            memory.chmod(0)
        done = _import(root, source, *flags, *(["--apply"] if apply else []), as_json=as_json)
    finally:
        if mode is not None:
            memory.chmod(mode)

    error, text = _error(done, as_json=as_json)
    if case == "remembered-date":
        assert "Remembered --date-format %d/%m/%Y does not match next.csv" in text
        _notes_first(error, text, REMEMBERED, as_json=as_json)
        assert "--date-format %d/%m/%Y" in text and "--account Assets:Checking" in text
    elif case == "remembered-codec":
        assert "next.csv is not valid cp1252" in text
        _notes_first(error, text, REMEMBERED, as_json=as_json)
        assert "encoding=cp1252" in text
        assert text.count("Remembered --csv encoding=cp1252 may misread next.csv") == 1
    elif case == "unreadable-memory":
        assert "next.csv is not valid UTF-8" in text
        _notes_first(error, text, UNREADABLE, as_json=as_json)
        assert str(memory) in text and "this run is not remembered" in text
        assert "Using settings remembered" not in text
    else:
        assert "cannot parse date '2026-03-99'" in text
        assert not error.get("details", [])
        assert "Using column mapping" not in text and REMEMBERED not in text and INFERRED not in text
    assert _snapshot(root) == before


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
@pytest.mark.parametrize("origin", ["remembered", "inferred"])
def test_incompatible_importer_selection_lists_the_actual_csv_settings(root: Path, origin: str, as_json: bool) -> None:
    if origin == "remembered":
        _seed(root)
    source = _source(root)
    before = _snapshot(root)
    flags = [] if origin == "remembered" else ["--account", "Assets:Checking"]

    done = _import(root, source, *flags, "--importer", "bank", as_json=as_json)

    error, text = _error(done, as_json=as_json)
    assert "--importer selects a Python importer by name" in text
    _notes_first(error, text, REMEMBERED if origin == "remembered" else INFERRED, as_json=as_json)
    assert _snapshot(root) == before


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_a_fully_typed_bad_amount_keeps_settings_out_of_error_details(root: Path, as_json: bool) -> None:
    source = _source(root, amount="not-money")
    before = _snapshot(root)

    done = _import(root, source, "--csv", MAPPING, "--account", "Assets:Checking", as_json=as_json)

    error, text = _error(done, as_json=as_json)
    assert "not-money" in text
    assert not error.get("details", [])
    assert REMEMBERED not in text and INFERRED not in text
    # Human output may have already printed the ordinary settings note before
    # the engine found the amount error. It must not be repeated as details.
    assert text.count("Using column mapping") <= 1
    assert _snapshot(root) == before


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_explicit_auto_still_has_an_inferred_mapping_in_its_date_refusal(root: Path, as_json: bool) -> None:
    source = _source(root, date="2026-03-99")
    before = _snapshot(root)

    done = _import(root, source, "--csv", "auto", "--account", "Assets:Checking", as_json=as_json)

    error, text = _error(done, as_json=as_json)
    assert "cannot parse date '2026-03-99'" in text
    _notes_first(error, text, INFERRED, as_json=as_json)
    assert _snapshot(root) == before


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_key_only_encoding_retains_recalled_columns_but_full_mapping_is_typed(root: Path, as_json: bool) -> None:
    _seed(root, encoding="cp1252")
    source = _source(root, description=b"Bad\x81")
    before = _snapshot(root)

    key_only = _import(root, source, "--csv", "encoding=cp1252", as_json=as_json)

    error, text = _error(key_only, as_json=as_json)
    assert "next.csv is not valid cp1252" in text
    _notes_first(error, text, REMEMBERED, as_json=as_json)
    assert "encoding=cp1252" in text
    assert "may misread" not in text  # The encoding was confirmed for this run.
    assert _snapshot(root) == before

    typed = _import(
        root, source, "--csv", f"{MAPPING},encoding=cp1252", "--account", "Assets:Checking", as_json=as_json
    )

    typed_error, typed_text = _error(typed, as_json=as_json)
    assert "next.csv is not valid cp1252" in typed_text
    assert not typed_error.get("details", [])
    assert REMEMBERED not in typed_text and INFERRED not in typed_text
    assert _snapshot(root) == before
