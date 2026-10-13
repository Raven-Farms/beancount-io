"""`check` reports an out-of-tree `option "documents"` folder once, at the option (w5/216).

Documents Beancount discovers from the option carry line 0 of the root ledger
and no written path, so the directive-level message blamed `main.bean:0`,
printed the absolute file name twice, advised "a relative path" for an option
that already was one, and repeated all of it for every file in the folder.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HEAD = 'option "operating_currency" "USD"\n'
BODY = (
    "2026-01-01 open Assets:Checking USD\n"
    "2026-01-01 open Equity:Opening\n"
    '2026-01-01 * "open"\n'
    "  Assets:Checking  100.00 USD\n"
    "  Equity:Opening\n"
)
STATEMENTS = ("2026-01-31.statement.pdf", "2026-02-28.statement.pdf")


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
        capture_output=True,
        text=True,
        timeout=60,
        stdin=subprocess.DEVNULL,
    )


def _ledger(tmp_path: Path, option: str, *, folder: Path, extra: str = "") -> Path:
    """`books/main.bean` with `option` on line 2 and two statements under `folder`."""
    (folder / "Assets" / "Checking").mkdir(parents=True)
    for name in STATEMENTS:
        (folder / "Assets" / "Checking" / name).write_bytes(b"%PDF")
    ledger = tmp_path / "books" / "main.bean"
    ledger.parent.mkdir(exist_ok=True)
    ledger.write_text(HEAD + option + BODY + extra)
    return ledger


def _details(result: subprocess.CompletedProcess[str]) -> list[str]:
    assert result.returncode == 1, result.stdout + result.stderr
    error = json.loads(result.stderr)["error"]
    assert error["category"] == "validation"
    details: list[str] = error["details"]
    return details


@pytest.mark.parametrize("absolute", [False, True], ids=["relative", "absolute"])
def test_an_out_of_tree_folder_is_one_finding_at_the_option_line(tmp_path: Path, absolute: bool) -> None:
    folder = tmp_path / "statements"
    value = str(folder) if absolute else "../statements"
    ledger = _ledger(tmp_path, f'option "documents" "{value}"\n', folder=folder)

    details = _details(_bea(tmp_path, "--json", "--file", str(ledger), "check"))

    assert len(details) == 1, details
    (line,) = details
    assert line.startswith(f'{ledger}:2: option "documents" "{value}" resolves to '), line
    assert f"{str(folder.resolve())!r}, outside the ledger directory" in line
    assert "(2 document(s) found there)" in line
    assert "Move the folder under the ledger directory" in line
    assert "main.bean:0" not in line
    assert "use a relative path" not in line
    assert not any(name in line for name in STATEMENTS)


def test_the_text_report_is_one_line_too(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, 'option "documents" "../statements"\n', folder=tmp_path / "statements")

    check = _bea(tmp_path, "--file", str(ledger), "check")

    assert check.returncode == 1, check.stdout + check.stderr
    assert "1 portable-document warning(s)." in check.stderr
    assert check.stderr.count('option "documents" "../statements"') == 1
    assert ".bean:0" not in check.stderr
    # The ledger itself is valid: only `check` objects to where the folder is.
    assert _bea(tmp_path, "--file", str(ledger), "balance").returncode == 0


def test_a_folder_inside_the_ledger_directory_passes(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path, 'option "documents" "docs"\n', folder=tmp_path / "books" / "docs")

    check = _bea(tmp_path, "--json", "--file", str(ledger), "check")

    assert check.returncode == 0, check.stdout + check.stderr
    assert json.loads(check.stdout)["data"] == {"valid": True, "errors": []}


def test_a_document_directive_is_still_reported_per_directive(tmp_path: Path) -> None:
    written = "../receipts/Assets/Checking/2026-01-31.statement.pdf"
    ledger = _ledger(
        tmp_path,
        'option "documents" "../statements"\n',
        folder=tmp_path / "statements",
        extra=f'2026-01-31 document Assets:Checking "{written}"\n',
    )
    (tmp_path / "receipts" / "Assets" / "Checking").mkdir(parents=True)
    (tmp_path / "receipts" / "Assets" / "Checking" / STATEMENTS[0]).write_bytes(b"%PDF")

    details = _details(_bea(tmp_path, "--json", "--file", str(ledger), "check"))

    assert len(details) == 2, details
    directive = [d for d in details if d.startswith(f"{ledger}:8: Document path {written!r}")]
    assert len(directive) == 1, details
    assert "use a relative path so copies stay portable" in directive[0]
    assert sum(d.startswith(f'{ledger}:2: option "documents"') for d in details) == 1
