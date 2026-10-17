"""`engine status` probes a `BEA_ENGINE_PYTHON` override and says when it cannot run the engine (w5/481).

Status named the override as serving, exit 0, with every optional feature
"present", while each local command failed and sent the user back to it.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _status(tmp_path: Path, python: str, *flags: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_ENGINE_PYTHON=python,
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *flags, "engine", "status"],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _old_python(tmp_path: Path) -> str:
    script = tmp_path / "python3.9"
    script.write_text(
        "#!/bin/sh\necho 'Unknown option: -P' >&2\necho 'usage: python3 [option] ...' >&2\n"
        'echo "Try \\`python -h\' for more information." >&2\nexit 2\n'
    )
    script.chmod(0o755)
    return str(script)


@pytest.mark.parametrize("kind", ["true", "old-python"])
def test_an_override_that_cannot_run_the_engine_is_reported(tmp_path: Path, kind: str) -> None:
    python = (shutil.which("true") or "/usr/bin/true") if kind == "true" else _old_python(tmp_path)
    reason = "it is not a Python that loads the engine" if kind == "true" else "Unknown option: -P; the engine needs"

    text = _status(tmp_path, python)
    assert text.returncode == 0, text.stderr
    assert f"Usable: no — it cannot load the engine ({reason}" in text.stdout
    assert "present" not in text.stdout

    data = json.loads(_status(tmp_path, python, "--json").stdout)["data"]
    assert data["usable"] is False
    assert data["unusable"].startswith(reason)
    assert not any(feature["present"] for feature in data["features"].values())


def test_a_working_override_reports_as_before(tmp_path: Path) -> None:
    text = _status(tmp_path, sys.executable)
    assert text.returncode == 0, text.stderr
    assert "Usable: no" not in text.stdout
    assert f"Engine interpreter override: {sys.executable}" in text.stdout

    data = json.loads(_status(tmp_path, sys.executable, "--json").stdout)["data"]
    assert data["usable"] is True
    assert "unusable" not in data
