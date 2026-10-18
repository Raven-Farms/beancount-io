"""Formatting to stdout or a destination must refuse syntax errors (w5/678)."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SENTINEL = b"LAST GOOD EXPORT\n"
BAD_INPUTS = [
    pytest.param('2026-01-01 open Assets:Cash USD\n2026-01-02 * "unterminated\n  Assets:Cash 1 USD\n', id="quote"),
    pytest.param("2026-01-01 open Assets:Cash USD\n2026-01-02 balance Assets:Cash USD\n", id="grammar"),
]
ZERO_DIVISOR = '2026-01-01 * "zero divisor"\n  Assets:Cash 100/0 USD\n  Equity:Opening\n'


def _bea(tmp_path: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_") and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=os.pathsep.join([str(ROOT / "src"), str(tmp_path)]),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", *args],
        env=env,
        cwd=tmp_path,
        input=stdin,
        stdin=None if stdin is not None else subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )


def _format(tmp_path: Path, text: str, source: str, mode: str) -> tuple[subprocess.CompletedProcess[str], Path]:
    original = tmp_path / "source.bean"
    original.write_text(text, encoding="utf-8")
    args = [*(["--json"] if mode == "json-output" else []), "format", "-" if source == "stdin" else str(original)]
    if mode != "stdout":
        args.extend(["-o", str(tmp_path / "formatted.out")])
    return _bea(tmp_path, *args, stdin=text if source == "stdin" else None), original


def _refusal(result: subprocess.CompletedProcess[str], original: Path, source: str, mode: str, line: int) -> str:
    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stdout == "", result.stdout
    assert "Traceback" not in result.stderr, result.stderr
    if mode == "json-output":
        error = json.loads(result.stderr)["error"]
        assert error["category"] == "validation", error
        assert error["exit_code"] == 1, error
        diagnostic = json.dumps(error, ensure_ascii=False)
    else:
        diagnostic = result.stderr
    if source == "stdin":
        assert "stdin" in diagnostic.casefold(), diagnostic
        assert re.search(rf":{line}\b", diagnostic), diagnostic
    else:
        assert f"{original}:{line}" in diagnostic, diagnostic
    return diagnostic


@pytest.mark.parametrize("text", BAD_INPUTS)
@pytest.mark.parametrize("source", ["file", "stdin"])
@pytest.mark.parametrize("mode", ["stdout", "output", "json-output"])
def test_render_modes_refuse_lexical_and_grammar_errors_without_writing(
    tmp_path: Path, text: str, source: str, mode: str
) -> None:
    destination = tmp_path / "formatted.out"
    # Both a new export and the previous good export must survive a refusal.
    for existing in [False, True] if mode != "stdout" else [False]:
        if existing:
            destination.write_bytes(SENTINEL)

        result, original = _format(tmp_path, text, source, mode)

        diagnostic = _refusal(result, original, source, mode, line=2)
        assert "parse" in diagnostic.casefold() or "syntax" in diagnostic.casefold(), diagnostic
        assert original.read_bytes() == text.encode()
        if existing:
            assert destination.read_bytes() == SENTINEL
        else:
            assert not destination.exists()


@pytest.mark.parametrize("source", ["file", "stdin"])
@pytest.mark.parametrize("mode", ["stdout", "json-output"])
def test_zero_divisor_is_a_named_validation_error_before_parser_or_output(
    tmp_path: Path, source: str, mode: str
) -> None:
    destination = tmp_path / "formatted.out"
    destination.write_bytes(SENTINEL)

    result, original = _format(tmp_path, ZERO_DIVISOR, source, mode)

    diagnostic = _refusal(result, original, source, mode, line=2)
    assert "Division by zero" in diagnostic, diagnostic
    assert "SIGSEGV" not in diagnostic, diagnostic
    assert original.read_bytes() == ZERO_DIVISOR.encode()
    assert destination.read_bytes() == SENTINEL


@pytest.mark.parametrize("source", ["file", "stdin"])
@pytest.mark.parametrize("mode", ["stdout", "output", "json-output"])
def test_render_only_checks_syntax_and_never_loads_plugins_or_includes(tmp_path: Path, source: str, mode: str) -> None:
    marker = tmp_path / "PLUGIN_RAN"
    (tmp_path / "must_not_run.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\nraise SystemExit(7)\n"
    )
    included = tmp_path / "broken.bean"
    included.write_text("this is not beancount\n")
    text = (
        'plugin "must_not_run"\n'
        'include "broken.bean"\n'
        'include "missing.bean"\n'
        "2026-01-01 open Assets:Cash USD\n"
        '2026-01-02 * "unbalanced and unopened account"\n'
        "    Assets:Cash      1.00 USD\n"
        "  Expenses:Unknown -2.00 USD\n"
        "2026-01-03 balance Assets:Cash 99 USD\n"
    )

    result, original = _format(tmp_path, text, source, mode)

    assert result.returncode == 0, result.stdout + result.stderr
    assert not marker.exists(), "formatting must not execute plugins"
    assert included.read_text() == "this is not beancount\n"
    assert original.read_bytes() == text.encode()
    if mode == "json-output":
        data = json.loads(result.stdout)["data"]
        assert data["scanned"] == (0 if source == "stdin" else 1), data
        assert data["output"] == str(tmp_path / "formatted.out"), data
    formatted = result.stdout if mode == "stdout" else (tmp_path / "formatted.out").read_text()
    assert formatted != text
    assert "\n  Assets:Cash " in formatted and "\n    Assets:Cash " not in formatted, formatted
    assert "Expenses:Unknown -2.00 USD" in " ".join(formatted.split()), formatted
    assert 'include "missing.bean"' in formatted and 'plugin "must_not_run"' in formatted, formatted


@pytest.mark.parametrize("source", ["file", "stdin"])
@pytest.mark.parametrize("spelling", ["plain", "bom", "nfd"])
def test_valid_input_keeps_supported_bom_and_account_spellings(tmp_path: Path, source: str, spelling: str) -> None:
    account = unicodedata.normalize("NFD", "Assets:Café") if spelling == "nfd" else "Assets:Cash"
    text = (
        f"2026-01-01 open {account} USD\n2026-01-01 open Equity:Opening USD\n"
        f'2026-01-02 * "ratio 3/0 is only text"\n    {account} 1 USD ; comment 1/0\n  Equity:Opening -1 USD\n'
    )
    if spelling == "bom":
        text = "\ufeff" + text

    result, original = _format(tmp_path, text, source, "stdout")

    assert result.returncode == 0, result.stdout + result.stderr
    assert not result.stdout.startswith("\ufeff")
    assert f"\n  {account} " in result.stdout
    assert '"ratio 3/0 is only text"' in result.stdout and "; comment 1/0" in result.stdout
    assert original.read_bytes() == text.encode()
