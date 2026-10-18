"""NFD account spellings cannot save an invalid import mapping or duplicate a valid one (w5/714)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = (
    'option "operating_currency" "EUR"\n'
    "2026-01-01 open Assets:Checking EUR\n"
    "2026-01-01 open Expenses:Uncategorized EUR\n"
)
MAPPING = "date=Date,narration=Description,amount=Amount"
NAMES = {"source": "Assets:Crédit", "default": "Expenses:Thé"}


@pytest.fixture
def root(tmp_path: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(LEDGER)
    (tmp_path / "plain.csv").write_text("Date,Description,Amount\n2026-03-01,Shop,-4.50\n")
    return path


def _import(root: Path, *args: str, as_json: bool = True) -> subprocess.CompletedProcess[str]:
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
            str(root.parent / "plain.csv"),
            *args,
        ],
        cwd=root.parent,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _data(done: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    assert done.returncode == 0, done.stdout + done.stderr
    return dict(json.loads(done.stdout)["data"])


def _memory(root: Path) -> dict[Path, bytes]:
    return {path: path.read_bytes() for path in (root.parent / "config" / "importers").glob("csv-*.json")}


def _entries(root: Path) -> list[dict[str, Any]]:
    (contents,) = _memory(root).values()
    return list(json.loads(contents)["sources"])


def _args(kind: str, account: str) -> list[str]:
    if kind == "source":
        return ["--csv", MAPPING, "--account", account]
    assert kind == "default"
    return ["--csv", MAPPING, "--account", "Assets:Checking", "--default-account", account]


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
@pytest.mark.parametrize("prior", [False, True], ids=["fresh-memory", "prior-valid-memory"])
@pytest.mark.parametrize("form", ["NFC", "NFD"])
@pytest.mark.parametrize("kind", ["source", "default"])
def test_a_preview_never_remembers_an_unopened_account_in_either_unicode_form(
    root: Path, kind: str, form: str, prior: bool, as_json: bool
) -> None:
    if prior:
        seeded = _data(_import(root, "--csv", MAPPING, "--account", "Assets:Checking"))
        assert seeded["ready"] == 1
    previous = _memory(root)
    before = root.read_bytes()
    source = root.parent / "plain.csv"
    source_before = source.read_bytes()
    canonical = NAMES[kind]
    typed = unicodedata.normalize(form, canonical)

    preview = _import(root, *_args(kind, typed), as_json=as_json)

    assert preview.returncode == 0, preview.stdout + preview.stderr
    notice = f"Not remembering these settings: {canonical} is not open in this ledger."
    if as_json:
        data = json.loads(preview.stdout)["data"]
        assert data["blocked"] == 1 and data["ready"] == 0
        assert canonical in data["unopened_accounts"]
        assert notice in data["notes"]
    else:
        assert notice in " ".join(preview.stderr.split())
        assert "1 blocked" in preview.stdout
    assert _memory(root) == previous
    assert root.read_bytes() == before and source.read_bytes() == source_before

    # A refused apply has always preserved memory too; keep that guarantee
    # alongside the preview path that originally saved the misspelled name.
    refused = _import(root, *_args(kind, typed), "--apply", as_json=as_json)
    assert refused.returncode == 4, refused.stdout + refused.stderr
    if as_json:
        error = json.loads(refused.stderr)["error"]
        assert error["category"] == "conflict"
        assert error["result"]["written"] == 0
    assert _memory(root) == previous
    assert root.read_bytes() == before and source.read_bytes() == source_before

    valid = _data(_import(root, "--csv", MAPPING, "--account", "Assets:Checking"))
    assert valid["ready"] == 1
    recalled = _data(_import(root))
    assert recalled["ready"] == 1 and recalled["blocked"] == 0
    assert recalled["account"] == "Assets:Checking"
    assert recalled["config_source"] == "remembered --csv"
    (entry,) = _entries(root)
    assert entry["account"] == "Assets:Checking"
    assert entry["default_account"] is None  # An omitted default follows the ledger's expense root.
    assert "Expenses:Uncategorized" in recalled["rows"][0]["entry"]
    assert root.read_bytes() == before


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
@pytest.mark.parametrize("kind", ["source", "default"])
def test_opened_nfd_names_are_saved_as_nfc_and_merge_with_the_existing_record(
    root: Path, kind: str, as_json: bool
) -> None:
    root.write_text(LEDGER + "2026-01-01 open Assets:Crédit EUR\n2026-01-01 open Expenses:Thé EUR\n")
    canonical = NAMES[kind]
    _data(_import(root, *_args(kind, canonical)))
    assert len(_entries(root)) == 1
    before = root.read_bytes()

    refreshed = _import(root, *_args(kind, unicodedata.normalize("NFD", canonical)), as_json=as_json)

    assert refreshed.returncode == 0, refreshed.stdout + refreshed.stderr
    assert "Not remembering these settings" not in refreshed.stdout + refreshed.stderr
    (entry,) = _entries(root)
    assert entry["account"] == (canonical if kind == "source" else "Assets:Checking")
    assert entry["default_account"] == (canonical if kind == "default" else None)
    assert unicodedata.is_normalized("NFC", entry["account"])
    if isinstance(entry["default_account"], str):
        assert unicodedata.is_normalized("NFC", entry["default_account"])

    recalled = _data(_import(root))

    assert recalled["ready"] == 1 and recalled["blocked"] == 0
    assert recalled["config_source"] == "remembered --csv"
    assert recalled["account"] == entry["account"]
    assert recalled["remembered"]["default_account"] == entry["default_account"]
    assert len(_entries(root)) == 1
    assert root.read_bytes() == before
