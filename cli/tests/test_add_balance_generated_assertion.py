"""`add balance` ignores an assertion a plugin synthesized: only written ones match or conflict (w5/152)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = 'plugin "beancount.plugins.check_drained"\n'
# check_drained asserts a zero balance the day after each close, stamped with
# the close's own line (line 9 once the plugin line leads the file).
LEDGER = """option "operating_currency" "USD"
2023-01-01 open Assets:Bank USD
2023-01-01 open Assets:Old USD
2023-01-01 open Equity:Opening
2023-01-02 * "Opening"
  Assets:Bank  1000.00 USD
  Equity:Opening
2023-02-01 close Assets:Old
"""
# check_closing does the same for a posting marked `closing: TRUE`.
CLOSING = """plugin "beancount.plugins.check_closing"
option "operating_currency" "USD"
2023-01-01 open Assets:Bank USD
2023-01-01 open Assets:Old USD
2023-01-02 * "Opening"
  Assets:Old  10 USD
  Assets:Bank
2023-02-01 * "Drain"
  Assets:Old  -10 USD
    closing: TRUE
  Assets:Bank
"""


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _add(tmp_path: Path, file: Path, amount: str, *extra: str) -> subprocess.CompletedProcess[str]:
    return _bea(
        tmp_path,
        "--json",
        "--file",
        str(file),
        "add",
        "balance",
        "-a",
        "Assets:Old",
        "--amount",
        amount,
        "--date",
        "2023-02-02",
        *extra,
    )


def _on_disk(tmp_path: Path, file: Path) -> list[dict[str, object]]:
    listed = _bea(tmp_path, "--json", "--file", str(file), "list", "balance", "--on-disk")
    assert listed.returncode == 0, listed.stderr
    rows: list[dict[str, object]] = json.loads(listed.stdout)["data"]
    return rows


@pytest.mark.parametrize("plugin", [PLUGIN, ""], ids=["check_drained", "control"])
def test_generated_assertion_is_not_already_recorded(tmp_path: Path, plugin: str) -> None:
    file = tmp_path / "main.bean"
    file.write_text(plugin + LEDGER)
    written_line = len(file.read_text().splitlines()) + 2  # a blank separator, then the directive
    assert _on_disk(tmp_path, file) == []

    first = _add(tmp_path, file, "0 USD")

    assert first.returncode == 0, first.stderr
    data = json.loads(first.stdout)["data"]
    assert data["written"] == 1 and data["duplicate"] is False
    assert file.read_text().count("2023-02-02 balance Assets:Old") == 1
    rows = _on_disk(tmp_path, file)
    assert [(row["date"], row["account"]) for row in rows] == [("2023-02-02", "Assets:Old")]
    # The written line is a real assertion: repeating it cites that line.
    after = file.read_bytes()
    again = _add(tmp_path, file, "0 USD")
    assert again.returncode == 0, again.stderr
    repeated = json.loads(again.stdout)["data"]
    assert repeated["written"] == 0 and repeated["duplicate"] is True
    assert repeated["source"]["lineno"] == written_line
    assert file.read_bytes() == after
    # ...and a different value for it is still a conflict naming that line.
    conflict = _add(tmp_path, file, "0.00 USD")
    assert conflict.returncode == 4, conflict.stderr
    assert f":{written_line}); refusing 0.00 USD" in conflict.stderr
    assert file.read_bytes() == after


def test_generated_assertion_is_not_a_conflict(tmp_path: Path) -> None:
    # A different precision than the plugin's `0 USD` was refused as a conflict
    # with the `close` line, though no assertion was written to correct.
    file = tmp_path / "main.bean"
    file.write_text(PLUGIN + LEDGER)

    result = _add(tmp_path, file, "0.00 USD")

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["data"]["written"] == 1
    assert "2023-02-02 balance Assets:Old" in file.read_text()
    assert "0.00 USD" in file.read_text()


def test_pad_from_retry_ignores_generated_assertion(tmp_path: Path) -> None:
    # The book already matches, so the pad goes unused and the retry writes the
    # assertion alone — it must not take the plugin's entry for a recorded one.
    file = tmp_path / "main.bean"
    file.write_text(PLUGIN + LEDGER)

    result = _add(tmp_path, file, "0 USD", "--pad-from", "Equity:Opening")

    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)["data"]
    assert data["written"] == 1, data
    text = file.read_text()
    assert text.count("2023-02-02 balance Assets:Old") == 1
    assert " pad " not in text


def test_check_closing_assertion_is_not_already_recorded(tmp_path: Path) -> None:
    file = tmp_path / "main.bean"
    file.write_text(CLOSING)

    result = _add(tmp_path, file, "0 USD")

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["data"]["written"] == 1
    assert file.read_text().count("2023-02-02 balance Assets:Old") == 1
