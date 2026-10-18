"""A nested Click refusal cannot prove that an engine write never started (w5/673)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = 'plugin "mutating_cli"\n2026-01-01 open Assets:Cash USD\n'
PERSISTED = "; plugin persisted an update\n"


@pytest.mark.parametrize("notice", [False, True], ids=["clean-click-diagnostic", "plugin-notice"])
@pytest.mark.parametrize("structured", [False, True], ids=["text", "json"])
def test_nested_click_exit_after_a_plugin_write_keeps_the_unknown_outcome(
    tmp_path: Path, notice: bool, structured: bool
) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(ORIGINAL)
    (tmp_path / "mutating_cli.py").write_text(
        "from pathlib import Path\n"
        "import click\n"
        '__plugins__ = ("run",)\n'
        "def run(entries, options):\n"
        '    with Path(__file__).with_name("main.bean").open("a", encoding="utf-8") as stream:\n'
        f"        stream.write({PERSISTED!r})\n"
        + ('    print("plugin persisted an update")\n' if notice else "")
        + '    click.Command("plugin-cli").main(args=["--bad-plugin-option"])\n'
        "    return entries, []\n"
    )
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_") and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        BEA_ENGINE_DIR=str(tmp_path / "engine"),
        BEA_NO_UPDATE_NOTIFIER="1",
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        PYTHONPATH=os.pathsep.join([str(ROOT / "src"), str(tmp_path)]),
        TERM="dumb",
        NO_COLOR="1",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cli.main",
            "--no-input",
            *(["--json"] if structured else []),
            "--file",
            str(ledger),
            "add",
            "open",
            "--date",
            "2026-02-03",
            "--account",
            "Assets:New",
        ],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 4, result.stdout + result.stderr
    assert result.stdout == ""
    if structured:
        error = json.loads(result.stderr)["error"]
        assert (error["category"], error["exit_code"]) == ("conflict", 4)
        assert "outcome is unknown" in error["message"]
        diagnostics = "\n".join(error["details"])
    else:
        assert "outcome is unknown" in result.stderr
        diagnostics = result.stderr
    assert "No such option: --bad-plugin-option" in diagnostics
    assert "Usage:" in diagnostics
    assert ("plugin persisted an update" in diagnostics) is notice
    assert "Traceback" not in result.stderr
    assert ledger.read_text() == ORIGINAL + PERSISTED
