"""Import refuses unreadable ledger syntax before advertising writable rows (w5/684)."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
HEADER = (
    'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n2026-01-01 open Expenses:Uncategorized USD\n'
)
CSV = "Date,Description,Amount\n2026-01-05,Coffee,-3.00\n"
SYNTAX = [
    pytest.param('2026-01-02 * "unterminated\n', "Invalid token", id="lexer"),
    pytest.param("2026-01-02 balance Assets:Cash USD\n", "syntax error", id="parser-syntax"),
]
IMPORTER = """\
import datetime
from decimal import Decimal
from pathlib import Path
from beancount.core import amount, data

Path(__file__).with_suffix(".loaded").write_text("loaded")


class MarkerImporter:
    name = "marker"

    def identify(self, filepath):
        return True

    def account(self, filepath):
        return "Assets:Cash"

    def extract(self, filepath, existing):
        Path(__file__).with_suffix(".extracted").write_text("extracted")
        return [data.Transaction(
            data.new_metadata(filepath, 1), datetime.date(2026, 1, 5), "*", None,
            "Configured Coffee", frozenset(), frozenset(), [
                data.Posting("Assets:Cash", amount.Amount(Decimal("-3"), "USD"), None, None, None, None),
                data.Posting("Expenses:Uncategorized", amount.Amount(Decimal("3"), "USD"), None, None, None, None),
            ],
        )]


CONFIG = [MarkerImporter()]
"""


def _books(tmp_path: Path, error: str, *, included: bool) -> tuple[Path, Path, int]:
    root = tmp_path / "main.bean"
    if included:
        root.write_text(HEADER + 'include "broken.bean"\n')
        error_file = tmp_path / "broken.bean"
        error_file.write_text(error)
        line = 1
    else:
        root.write_text(HEADER + error)
        error_file = root
        line = len(HEADER.splitlines()) + 1
    (tmp_path / "statement.csv").write_text(CSV)
    return root, error_file, line


def _run(
    root: Path,
    *,
    json_output: bool,
    apply: bool = False,
    allow_errors: bool = False,
    config: Path | None = None,
) -> subprocess.CompletedProcess[str]:
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
    mode = (
        ["--config", str(config)]
        if config is not None
        else ["--csv", "date=Date,amount=Amount,narration=Description", "--account", "Assets:Cash"]
    )
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "cli.main",
            "--no-input",
            *(["--json"] if json_output else []),
            "--file",
            str(root),
            "import",
            str(root.parent / "statement.csv"),
            *mode,
            *(["--allow-errors"] if allow_errors else []),
            *(["--apply"] if apply else []),
        ],
        env=env,
        cwd=root.parent,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _failure(result: subprocess.CompletedProcess[str], json_output: bool) -> tuple[str, str, dict[str, Any]]:
    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stdout == "", result.stdout
    assert "Traceback" not in result.stderr, result.stderr
    if json_output:
        error = json.loads(result.stderr)["error"]
        assert error["category"] == "validation" and error["exit_code"] == 1, error
        return error["message"], " ".join([error["message"], *error.get("details", [])]), error.get("result") or {}
    return result.stderr, result.stderr, {}


def _syntax_refusal(result: subprocess.CompletedProcess[str], json_output: bool, source: Path, line: int) -> str:
    message, diagnostic, preview = _failure(result, json_output)
    assert "including a syntax error" in message, message
    assert "Fix the syntax error first: --allow-errors never writes past one." in message, message
    assert "Pass --allow-errors" not in diagnostic, diagnostic
    assert f"{source}:{line}:" in diagnostic, diagnostic
    assert preview.get("ready", 0) == 0 and not preview.get("rows") and not preview.get("diff"), preview
    assert "Preview only" not in result.stdout + result.stderr
    assert "repeat with --apply" not in result.stdout + result.stderr
    assert not re.search(r"\b[1-9]\d* ready\b", result.stdout + result.stderr)
    return diagnostic


@pytest.mark.parametrize(("bad", "diagnostic"), SYNTAX)
@pytest.mark.parametrize("included", [False, True], ids=["root", "include"])
@pytest.mark.parametrize("json_output", [False, True], ids=["human", "json"])
@pytest.mark.parametrize("apply", [False, True], ids=["preview", "apply"])
@pytest.mark.parametrize("allow_errors", [False, True], ids=["strict", "allow-errors"])
def test_syntax_errors_refuse_every_preview_and_apply_without_ready_rows(
    tmp_path: Path, bad: str, diagnostic: str, included: bool, json_output: bool, apply: bool, allow_errors: bool
) -> None:
    root, source, line = _books(tmp_path, bad, included=included)
    before = {path: path.read_bytes() for path in tmp_path.iterdir() if path.is_file()}

    result = _run(root, json_output=json_output, apply=apply, allow_errors=allow_errors)

    details = _syntax_refusal(result, json_output, source, line)
    assert diagnostic.casefold() in details.casefold(), details
    assert {path: path.read_bytes() for path in before} == before
    assert not list(tmp_path.glob(".bea-*"))


@pytest.mark.parametrize("json_output", [False, True], ids=["human", "json"])
@pytest.mark.parametrize("apply", [False, True], ids=["preview", "apply"])
def test_fatal_syntax_is_detected_before_loading_or_running_a_configured_importer(
    tmp_path: Path, json_output: bool, apply: bool
) -> None:
    bad = "2026-01-02 balance Assets:Cash USD\n"
    root, source, line = _books(tmp_path, bad, included=True)
    config = tmp_path / "marker_importer.py"
    config.write_text(IMPORTER)
    before = {path: path.read_bytes() for path in (root, source, config, tmp_path / "statement.csv")}

    result = _run(root, json_output=json_output, apply=apply, allow_errors=True, config=config)

    _syntax_refusal(result, json_output, source, line)
    assert not config.with_suffix(".loaded").exists()
    assert not config.with_suffix(".extracted").exists()
    assert {path: path.read_bytes() for path in before} == before

    # The same real configuration executes once the ledger syntax is repaired.
    source.write_text("")
    cleaned = {root: root.read_bytes(), source: source.read_bytes()}
    preview = _run(root, json_output=json_output, config=config)
    assert preview.returncode == 0, preview.stdout + preview.stderr
    assert config.with_suffix(".loaded").read_text() == "loaded"
    assert config.with_suffix(".extracted").read_text() == "extracted"
    if json_output:
        data = json.loads(preview.stdout)["data"]
        assert data["ready"] == 1 and data["written"] == 0, data
    else:
        assert "Preview only" in preview.stdout, preview.stdout
    assert {path: path.read_bytes() for path in cleaned} == cleaned


@pytest.mark.parametrize(
    ("diagnostic", "expected"),
    [
        ("2026-01-02 balance Assets:Cash 7 USD\n", "Balance failed"),
        ('option "experiment_explicit_tolerances" "TRUE"\n', "Invalid option"),
    ],
    ids=["existing-balance-error", "semantic-parser-error"],
)
@pytest.mark.parametrize("json_output", [False, True], ids=["human", "json"])
@pytest.mark.parametrize("apply", [False, True], ids=["preview", "apply"])
def test_semantic_errors_keep_accurate_flag_advice_and_allow_real_preview_or_apply(
    tmp_path: Path, diagnostic: str, expected: str, json_output: bool, apply: bool
) -> None:
    root, source, line = _books(tmp_path, diagnostic, included=False)
    before = root.read_bytes()

    refused = _run(root, json_output=json_output, apply=apply)
    message, details, _ = _failure(refused, json_output)
    assert "Pass --allow-errors to write anyway." in message, message
    assert expected in details and f"{source}:{line}:" in details, details
    assert "Fix the syntax error first" not in message
    assert root.read_bytes() == before

    allowed = _run(root, json_output=json_output, apply=apply, allow_errors=True)

    assert allowed.returncode == 0, allowed.stdout + allowed.stderr
    if json_output:
        data = json.loads(allowed.stdout)["data"]
        assert data["ready"] == 1 and data["written"] == int(apply), data
        assert data["validation_errors"] == [], data
        assert any(expected in warning for warning in data["validation_warnings"]), data
    elif not apply:
        assert "Preview only" in allowed.stdout, allowed.stdout
    if apply:
        assert root.read_bytes().startswith(before) and root.read_bytes() != before
        assert '"Coffee"' in root.read_text()[len(before.decode()) :]
    else:
        assert root.read_bytes() == before
