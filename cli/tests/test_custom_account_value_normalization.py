"""`add custom --value account:…` takes an account typed in NFD (w5/130).

Every other `add` command accepted the decomposed spelling a macOS file name
or a paste yields and wrote it NFC. `add custom` rendered the line NFC and then
compared its reload against the raw NFD request, so it refused its own output
with "would reload as different values" and two lines that look identical.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

NFC = unicodedata.normalize("NFC", "Assets:Élan")
NFD = unicodedata.normalize("NFD", "Assets:Élan")
LEDGER = f"""option "operating_currency" "USD"
2020-01-01 open {NFC} USD
2020-01-01 open Equity:Opening
"""


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "--file", str(tmp_path / "main.bean"), *args],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        stdin=subprocess.DEVNULL,
        timeout=60,
    )


def _ledger(tmp_path: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")
    return ledger


@pytest.mark.parametrize("typed", [NFD, NFC], ids=["nfd", "nfc"])
def test_custom_account_value_is_written_nfc(tmp_path: Path, typed: str) -> None:
    assert NFD != NFC
    ledger = _ledger(tmp_path)

    result = _bea(
        tmp_path,
        *("add", "custom", "--date", "2021-01-05", "--type", "budget"),
        *("--value", f"account:{typed}", "--value", "amount:5 USD"),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert ledger.read_text(encoding="utf-8") == LEDGER + f'\n2021-01-05 custom "budget" {NFC} 5 USD\n'
    values = json.loads(result.stdout)["data"]["directive"]["values"]
    assert values[0] == {"kind": "account", "value": NFC}


def test_other_custom_value_kinds_keep_their_text(tmp_path: Path) -> None:
    """Only account values are names; a text value typed in NFD is the user's own bytes."""
    ledger = _ledger(tmp_path)
    text = unicodedata.normalize("NFD", "Élan")

    result = _bea(
        tmp_path,
        *("add", "custom", "--date", "2021-01-05", "--type", "budget"),
        *("--value", f"text:{text}", "--value", "number:5", "--value", "bool:true", "--value", "date:2021-02-01"),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert ledger.read_text(encoding="utf-8") == LEDGER + f'\n2021-01-05 custom "budget" "{text}" 5 TRUE 2021-02-01\n'


def test_note_control_accepts_the_same_spelling(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)

    result = _bea(tmp_path, "add", "note", "--account", NFD, "--comment", "hi", "--date", "2021-01-05")

    assert result.returncode == 0, result.stdout + result.stderr
    assert ledger.read_text(encoding="utf-8") == LEDGER + f'\n2021-01-05 note {NFC} "hi"\n'
