"""`bea check --json` (bean-check's flag) carries bea's own findings in its JSON list (w5/496).

Plugin failures, portable-document warnings and undecodable files were
printed as text on stderr, so stdout read `{"errors": []}` or nothing at all
while the exit status said the check failed.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _check(tmp_path: Path, ledger: Path) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(ledger), "check", "--json"],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _portable(tmp_path: Path) -> Path:
    (tmp_path / "books").mkdir()
    (tmp_path / "outside").mkdir()
    (tmp_path / "outside" / "r.pdf").write_bytes(b"%PDF")
    ledger = tmp_path / "books" / "main.bean"
    ledger.write_text('2024-01-01 open Assets:Cash USD\n2024-01-02 document Assets:Cash "../outside/r.pdf"\n')
    return ledger


def _plugin(tmp_path: Path) -> Path:
    ledger = tmp_path / "plug.bean"
    ledger.write_text('plugin "no_such_plugin_xyz"\n2024-01-01 open Assets:Cash USD\n')
    return ledger


def _latin(tmp_path: Path) -> Path:
    ledger = tmp_path / "latin.bean"
    ledger.write_bytes(b'2024-01-01 open Assets:Cash USD\n2024-01-02 note Assets:Cash "caf\xe9"\n')
    return ledger


@pytest.mark.parametrize(
    ("make", "says", "line"),
    [
        (_portable, "outside the ledger directory", 2),
        (_plugin, 'Cannot import plugin "no_such_plugin_xyz"', 1),
        (_latin, "as UTF-8", 0),
    ],
    ids=["portable-document", "plugin", "undecodable"],
)
def test_the_finding_is_in_the_json_list(tmp_path: Path, make: object, says: str, line: int) -> None:
    ledger = make(tmp_path)  # type: ignore[operator]

    result = _check(tmp_path, ledger)

    assert result.returncode == 1, result.stdout + result.stderr
    errors = json.loads(result.stdout)["errors"]
    assert len(errors) == 1
    assert says in errors[0]["message"]
    assert errors[0]["lineno"] == line
    assert errors[0]["filename"].endswith(ledger.name)


def test_bean_checks_own_errors_are_unchanged(tmp_path: Path) -> None:
    ledger = tmp_path / "bad.bean"
    ledger.write_text("2024-01-01 open Assets:Cash USD\n2024-01-02 balance Assets:Cash 5 USD\n")

    result = _check(tmp_path, ledger)

    assert result.returncode == 1
    assert json.loads(result.stdout)["errors"][0]["message"].startswith("Balance failed for 'Assets:Cash'")
