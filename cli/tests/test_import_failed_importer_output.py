"""What an importer printed survives the exception it then raises (w5/143).

Importer output is captured so it cannot corrupt the JSON envelope, and a
successful preview hands it back as `importer_output`. When `extract` raised,
the capture was dropped with the preview: the prints that lead up to the
failure reached neither stderr, `--debug`, nor the JSON error.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

LEDGER = (
    'option "operating_currency" "USD"\n'
    "2026-01-01 open Assets:Checking USD\n"
    "2026-01-01 open Expenses:Uncategorized USD\n"
)

IMPORTER = textwrap.dedent("""
    import subprocess, sys

    class Noisy:
        name = "noisy"

        def identify(self, filepath):
            return True

        def account(self, filepath):
            return "Assets:Checking"

        def extract(self, filepath, existing):
            name = str(filepath)
            if name.endswith("quiet.txt"):
                raise ValueError("nothing was printed")
            print("DEBUG row 7 date cell = '31/02/2026'")
            print("WARN: skipping malformed row", file=sys.stderr)
            subprocess.run([sys.executable, "-c", "print('child process line')"], check=True)
            if name.endswith("bad.txt"):
                raise ValueError("day is out of range for month")
            if name.endswith("missing.txt"):
                import a_module_no_engine_has_w5_143
            return []

    CONFIG = [Noisy()]
""")

PRINTED = ("DEBUG row 7 date cell = '31/02/2026'", "WARN: skipping malformed row", "child process line")


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
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def _books(tmp_path: Path, export: str) -> list[str]:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")
    config = tmp_path / "importers.py"
    config.write_text(IMPORTER, encoding="utf-8")
    source = tmp_path / export
    source.write_text("x\n", encoding="utf-8")
    return ["--file", str(ledger), "import", str(source), "--config", str(config)]


@pytest.mark.parametrize("debug", [False, True])
def test_failing_importer_output_precedes_the_error_on_stderr(tmp_path: Path, debug: bool) -> None:
    done = _bea(tmp_path, *(["--debug"] if debug else []), *_books(tmp_path, "bad.txt"))

    assert done.returncode == 1, done.stderr
    assert done.stdout == ""
    error_at = done.stderr.index("Error: Importer failed (ValueError): day is out of range for month.")
    for text in PRINTED:
        assert text in done.stderr[:error_at], done.stderr
    assert ("Traceback (most recent call last)" in done.stderr) is debug


def test_failing_importer_output_is_in_the_json_error(tmp_path: Path) -> None:
    done = _bea(tmp_path, "--json", *_books(tmp_path, "bad.txt"))

    assert done.returncode == 1, done.stderr
    assert done.stdout == ""
    error = json.loads(done.stderr)["error"]
    assert error["category"] == "validation"
    assert error["message"].startswith("Importer failed (ValueError): day is out of range for month.")
    for text in PRINTED:
        assert text in error["result"]["importer_output"]


def test_missing_importer_dependency_keeps_the_output_too(tmp_path: Path) -> None:
    done = _bea(tmp_path, "--json", *_books(tmp_path, "missing.txt"))

    assert done.returncode == 2, done.stderr
    assert done.stdout == ""
    error = json.loads(done.stderr)["error"]
    assert error["category"] == "usage"
    for text in PRINTED:
        assert text in error["result"]["importer_output"]


def test_silent_failing_importer_adds_no_result(tmp_path: Path) -> None:
    done = _bea(tmp_path, "--json", *_books(tmp_path, "quiet.txt"))

    assert done.returncode == 1, done.stderr
    error = json.loads(done.stderr)["error"]
    assert error["message"].startswith("Importer failed (ValueError): nothing was printed.")
    assert "result" not in error


def test_successful_importer_output_is_unchanged(tmp_path: Path) -> None:
    argv = _books(tmp_path, "ok.txt")

    text = _bea(tmp_path, *argv)
    assert text.returncode == 0, text.stderr
    for line in PRINTED:
        assert line in text.stderr
        assert line not in text.stdout
    assert "Error:" not in text.stderr

    done = _bea(tmp_path, "--json", *argv)
    assert done.returncode == 0, done.stderr
    assert done.stderr == ""
    answer = json.loads(done.stdout)["data"]
    for line in PRINTED:
        assert line in answer["importer_output"]
