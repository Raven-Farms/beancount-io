"""`--json` shows what a ledger plugin printed on stderr, after the envelope (w5/270).

Text mode printed a plugin's output on stderr, as docs/USAGE.md promises.
Under `--json` the same lines appeared nowhere, so a plugin's diagnostics
vanished from automated runs.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import typer

from cli import output

ROOT = Path(__file__).resolve().parents[1]

LEDGER = (
    'option "operating_currency" "USD"\n'
    'option "insert_pythonpath" "TRUE"\n'
    'plugin "noisy"\n'
    "2026-01-01 open Assets:Cash USD\n"
    "2026-01-01 open Expenses:Food USD\n"
    '2026-01-02 * "x"\n'
    "  Expenses:Food  1.00 USD\n"
    "  Assets:Cash\n"
)

PLUGIN = (
    "import sys\n"
    '__plugins__ = ["noisy"]\n'
    "def noisy(entries, options_map, config=None):\n"
    '    print("PLUGIN-PRINT"); sys.stdout.flush()\n'
    '    sys.stderr.write("PLUGIN-STDERR\\n")\n'
    "    return entries, []\n"
)

MARKERS = ["PLUGIN-PRINT", "PLUGIN-STDERR"]


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER, encoding="utf-8")
    (tmp_path / "noisy.py").write_text(PLUGIN, encoding="utf-8")
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


@pytest.mark.parametrize("command", [["balance"], ["check"], ["list", "transaction"]])
def test_json_mode_prints_plugin_output_on_stderr(tmp_path: Path, command: list[str]) -> None:
    done = _bea(tmp_path, "--json", "-f", "main.bean", *command)

    assert done.returncode == 0, done.stderr
    assert done.stderr.splitlines() == MARKERS
    # stdout is still exactly the envelope.
    assert "data" in json.loads(done.stdout)
    assert "PLUGIN" not in done.stdout


def test_text_mode_still_prints_plugin_output_on_stderr(tmp_path: Path) -> None:
    done = _bea(tmp_path, "-f", "main.bean", "balance")

    assert done.returncode == 0, done.stderr
    assert done.stderr.splitlines() == MARKERS
    assert "PLUGIN" not in done.stdout


def test_a_json_failure_still_leaves_one_object_on_stderr(tmp_path: Path) -> None:
    done = _bea(tmp_path, "--json", "-f", "main.bean", "query", "SELECT nosuch")

    assert done.returncode == 2
    assert done.stdout == ""
    assert json.loads(done.stderr)["error"]["category"] == "usage"


def test_a_failure_after_a_successful_engine_call_drops_the_plugin_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(output, "_json_mode", lambda: True)
    output.engine_output("PLUGIN-PRINT")

    with pytest.raises(typer.Exit):
        output.error("later failure")
    output.flush_warnings()

    captured = capsys.readouterr()
    assert json.loads(captured.err)["error"]["message"] == "later failure"
    assert captured.out == ""
