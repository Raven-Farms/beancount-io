"""An importer configuration that calls `sys.exit` is an importer failure (w5/634).

A Beangulp ingest script reused as `--config` without an
`if __name__ == "__main__":` guard runs `Ingest(CONFIG)()` on load, and Click
exits. `SystemExit` passed the importer guard: the preview said the engine
"did not answer", and `--apply` exited 4 with "the outcome is unknown",
though the importer runs before anything is written. What it printed, which
explained it, was thrown away.
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
LEDGER = "2026-01-01 open Assets:Bank USD\n2026-01-01 open Expenses:Food USD\n"
AT_LOAD = textwrap.dedent("""
    import sys
    print("Error: No such command 'import'.", file=sys.stderr)
    sys.exit(2)
""")
IN_EXTRACT = textwrap.dedent("""
    import sys

    class Bank:
        name = "bank"

        def identify(self, filepath):
            return True

        def account(self, filepath):
            return "Assets:Bank"

        def extract(self, filepath, existing):
            print("done early")
            sys.exit(0)

    CONFIG = [Bank()]
""")
HINT = 'Put that call under if __name__ == "__main__": to use the script with --config.'


def _bea(tmp_path: Path, config: str, *extra: str, json_output: bool = False) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "bank.txt").write_text("x\n")
    (tmp_path / "imp.py").write_text(config)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *(["--json"] if json_output else []), "--no-input", "-f", "main.bean"]
        + ["import", "bank.txt", "--config", "imp.py", *extra],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
        check=False,
    )


@pytest.mark.parametrize(
    ("config", "said", "printed"),
    [
        (AT_LOAD, "Importer failed (SystemExit: 2): the configuration called sys.exit", "No such command"),
        # An exit in a method is the method's, not the module's: no Ingest hint (w5/852).
        (
            IN_EXTRACT,
            "Importer bank extract() called sys.exit (0); an importer method must return its answer or raise",
            "done early",
        ),
    ],
    ids=["at-load", "in-extract"],
)
@pytest.mark.parametrize("apply", [False, True], ids=["preview", "apply"])
def test_sys_exit_is_an_importer_failure(tmp_path: Path, config: str, said: str, printed: str, apply: bool) -> None:
    result = _bea(tmp_path, config, *(["--apply"] if apply else []))

    assert result.returncode == 1, result.stderr
    stderr = " ".join(result.stderr.split())
    assert said in stderr
    assert (HINT in stderr) is (config == AT_LOAD)
    assert printed in stderr
    assert "did not answer" not in stderr and "outcome is unknown" not in stderr
    assert (tmp_path / "main.bean").read_text() == LEDGER


def test_json_carries_what_it_printed(tmp_path: Path) -> None:
    result = _bea(tmp_path, AT_LOAD, json_output=True)

    assert result.returncode == 1
    error = json.loads(result.stderr)["error"]
    assert error["message"].startswith("Importer failed (SystemExit: 2)")
    assert error["result"]["importer_output"] == "Error: No such command 'import'.\n"
