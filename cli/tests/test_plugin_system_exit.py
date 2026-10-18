"""Plugin SystemExit is a named load failure on every CLI surface (w5/674)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ENTRIES = """2026-01-01 open Assets:Cash USD
2026-01-01 open Equity:Opening USD
2026-01-02 * "Opening"
  Assets:Cash 73 USD
  Equity:Opening
"""
SURFACES = [
    "check",
    "check-json",
    "list-json",
    "add-json",
    "doctor-missing-open",
    "doctor-roundtrip",
    "source-path",
    "source-uri",
]
REASONS = {"argparse": "2", "zero": "0", "seven": "7", "message": "bad config from plugin"}


def _books(directory: Path, kind: str, *, at_import: bool = False) -> Path:
    ledger = directory / "main.bean"
    config = "--treshold=5" if kind == "argparse" else "config"
    ledger.write_text('option "insert_pythonpath" "TRUE"\n' + f'plugin "argplug" "{config}"\n' + ENTRIES)
    if kind == "argparse":
        body = (
            '    parser = argparse.ArgumentParser(prog="argplug")\n'
            '    parser.add_argument("--threshold", type=int, default=0)\n'
            "    parser.parse_args(shlex.split(config))\n"
        )
    elif kind == "value-error":
        body = '    raise ValueError("bad plugin value")\n'
    elif kind == "clean":
        body = ""
    else:
        value = {"zero": "0", "seven": "7", "message": repr(REASONS["message"])}[kind]
        body = f"    sys.exit({value})\n"
    module = "import argparse\nimport shlex\nimport sys\n"
    if at_import:
        module += body.removeprefix("    ")
    else:
        module += (
            '__plugins__ = ("argplug",)\ndef argplug(entries, options, config=""):\n'
            + body
            + "    return entries, []\n"
        )
    (directory / "argplug.py").write_text(module)
    return ledger


def _run(
    directory: Path, ledger: Path, surface: str, *, extra: tuple[str, ...] = ()
) -> subprocess.CompletedProcess[str]:
    structured = surface.endswith("-json") and surface != "native-check-json"
    debug = surface.startswith("debug-")
    if "check" in surface:
        command = ["check", *(["--json"] if surface == "native-check-json" else [])]
    elif surface.startswith("list"):
        command = ["list", "transaction"]
    elif surface.startswith("add"):
        command = ["add", "open", "--date", "2026-02-03", "--account", "Assets:New"]
    elif surface.startswith("balance"):
        command = ["balance"]
    elif surface.startswith("doctor-"):
        command = ["doctor", surface.removeprefix("doctor-"), str(ledger)]
    else:
        source = str(ledger) if surface == "source-path" else f"beancount:{ledger}"
        command = ["query", "--source", source, "SELECT 73 AS n LIMIT 1"]
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_") and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    env.update(
        BEA_CONFIG_DIR=str(directory / "config"),
        BEA_ENGINE_DIR=str(directory / "engine"),
        BEA_NO_UPDATE_NOTIFIER="1",
        XDG_CACHE_HOME=str(directory / "cache"),
        XDG_DATA_HOME=str(directory / "data"),
        PYTHONPATH=os.pathsep.join([str(ROOT / "src"), str(directory)]),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "cli.main",
            "--no-input",
            *(["--debug"] if debug else []),
            *(["--json"] if structured else []),
            *([] if command[0] == "doctor" else ["--file", str(ledger)]),
            *command,
            *extra,
        ],
        cwd=directory,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _failure(result: subprocess.CompletedProcess[str], surface: str) -> str:
    assert result.returncode == 1, result.stdout + result.stderr
    if surface == "native-check-json":
        errors = json.loads(result.stdout)["errors"]
        assert errors, result.stdout
        text = "\n".join(error["message"] for error in errors) + result.stderr
    elif surface.endswith("-json"):
        assert result.stdout == ""
        error = json.loads(result.stderr)["error"]
        assert (error["category"], error["exit_code"]) == ("validation", 1), error
        text = error["message"] + "\n" + "\n".join(error.get("details", []))
    else:
        assert result.stdout == "", result.stdout
        text = result.stderr
    for misleading in ("engine did not answer", "outcome is unknown"):
        assert misleading not in text
    return text


@pytest.mark.parametrize("kind", REASONS)
@pytest.mark.parametrize("surface", SURFACES)
def test_callback_exit_is_a_named_plugin_failure(tmp_path: Path, kind: str, surface: str) -> None:
    ledger = _books(tmp_path, kind)
    before = ledger.read_bytes()

    result = _run(tmp_path, ledger, surface)

    message = _failure(result, surface)
    assert 'Plugin "argplug" failed while running:' in message
    assert f"SystemExit: {REASONS[kind]}" in message
    if kind == "argparse":
        assert "unrecognized arguments: --treshold=5" in message
    assert ledger.read_bytes() == before


@pytest.mark.parametrize("kind", ["argparse", "zero"])
@pytest.mark.parametrize("surface", ["list", "add", "debug-check", "debug-check-json", "native-check-json"])
def test_exit_failures_also_cover_text_debug_and_native_json(tmp_path: Path, kind: str, surface: str) -> None:
    ledger = _books(tmp_path, kind)
    before = ledger.read_bytes()

    result = _run(tmp_path, ledger, surface)

    message = _failure(result, surface)
    assert 'Plugin "argplug" failed while running:' in message
    assert f"SystemExit: {REASONS[kind]}" in message
    if kind == "argparse":
        assert "unrecognized arguments: --treshold=5" in message
    assert ledger.read_bytes() == before


@pytest.mark.parametrize("kind", ["zero", "seven"])
@pytest.mark.parametrize("surface", ["check-json", "add-json"])
def test_import_time_exit_is_also_a_named_plugin_failure(tmp_path: Path, kind: str, surface: str) -> None:
    ledger = _books(tmp_path, kind, at_import=True)
    before = ledger.read_bytes()

    result = _run(tmp_path, ledger, surface)

    message = _failure(result, surface)
    assert 'Cannot import plugin "argplug"' in message
    assert f"SystemExit: {REASONS[kind]}" in message
    assert ledger.read_bytes() == before


@pytest.mark.parametrize("surface", ["check-json", "add-json"])
def test_existing_value_error_reporting_is_unchanged(tmp_path: Path, surface: str) -> None:
    ledger = _books(tmp_path, "value-error")
    before = ledger.read_bytes()

    result = _run(tmp_path, ledger, surface)

    message = _failure(result, surface)
    assert 'Plugin "argplug" failed while running: ValueError: bad plugin value.' in message
    assert ledger.read_bytes() == before


@pytest.mark.parametrize("surface", ["check-json", "add-json"])
def test_a_clean_plugin_still_checks_and_writes(tmp_path: Path, surface: str) -> None:
    ledger = _books(tmp_path, "clean")
    before = ledger.read_bytes()

    result = _run(tmp_path, ledger, surface)

    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(result.stdout)["data"]
    if surface == "check-json":
        assert data["valid"] is True
        assert ledger.read_bytes() == before
    else:
        assert data["written"] == 1
        assert "Assets:New" in ledger.read_text()


@pytest.mark.parametrize("surface", ["balance-json", "add-json"])
def test_exit_without_a_value_keeps_descriptor_output_and_stops_even_with_allow_errors(
    tmp_path: Path, surface: str
) -> None:
    ledger = _books(tmp_path, "zero")
    before = ledger.read_bytes()
    (tmp_path / "argplug.py").write_text(
        "import os, subprocess, sys\n"
        "from pathlib import Path\n"
        '__plugins__ = ("argplug", "after")\n'
        'def argplug(entries, options, config=""):\n'
        '    os.write(1, b"descriptor one output\\n")\n'
        '    os.write(2, b"descriptor two output\\n")\n'
        '    subprocess.run([sys.executable, "-c", "print(\'plugin child output\')"], check=True)\n'
        "    sys.exit()\n"
        'def after(entries, options, config=""):\n'
        '    Path(__file__).with_name("after-ran").touch()\n'
        "    return entries, []\n"
    )

    result = _run(tmp_path, ledger, surface, extra=("--allow-errors",))

    message = _failure(result, surface)
    assert 'Plugin "argplug" failed while running: SystemExit' in message
    for output in ("descriptor one output", "descriptor two output", "plugin child output"):
        assert output in message
    assert not (tmp_path / "after-ran").exists()
    assert ledger.read_bytes() == before
