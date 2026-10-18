"""Flag metadata preserves wide decimal digits in numbers and amounts (w5/669)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NUMBERS = ["12345678901.123456789012345678", "1234567890.123456789012345678"]
COMMANDS = [
    ("transaction", "A", "-p", "Assets:Wallet 1 SHIB", "-p", "Equity:Opening"),
    ("commodity", "--commodity", "SHIB"),
]


@pytest.mark.parametrize("command", COMMANDS, ids=lambda args: args[0])
@pytest.mark.parametrize("number", NUMBERS, ids=["29-digits", "28-digit-control"])
@pytest.mark.parametrize("json_mode", [False, True], ids=["text", "json"])
def test_metadata_numbers_and_amounts_keep_the_typed_digits(
    tmp_path: Path,
    command: tuple[str, ...],
    number: str,
    json_mode: bool,
) -> None:
    ledger = tmp_path / "main.bean"
    original = "2026-01-01 open Assets:Wallet\n2026-01-01 open Equity:Opening\n"
    ledger.write_text(original)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
        TERM="dumb",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cli.main",
            *(["--json"] if json_mode else []),
            "--file",
            str(ledger),
            "add",
            *command,
            "--date",
            "2026-02-01",
            "--meta",
            f"qty: -{number}",
            "--meta",
            f"pos: {number}",
            "--meta",
            f"fee: -{number} SHIB",
        ],
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    written = ledger.read_text()
    assert written.startswith(original)
    assert f"  qty: -{number}\n" in written
    assert f"  pos: {number}\n" in written
    assert f"  fee: -{number} SHIB\n" in written
    if json_mode:
        meta = json.loads(result.stdout)["data"]["directive"]["meta"]
        assert meta == {
            "qty": {"kind": "number", "value": f"-{number}"},
            "pos": {"kind": "number", "value": number},
            "fee": {"kind": "amount", "number": f"-{number}", "currency": "SHIB"},
        }
