"""`BEA_ENGINE_DIR` is checked before use, like `BEA_CONFIG_DIR` (w5/412).

A relative value would provision a whole engine into every working
directory, and a regular file can never hold one, yet `engine status`
reported both as an engine location with exit 0.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _status(tmp_path: Path, engine_dir: str, *, json_output: bool = False) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_ENGINE_DIR=engine_dir,
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *(["--json"] if json_output else []), "engine", "status"],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
        stdin=subprocess.DEVNULL,
    )


def test_a_relative_path_is_refused(tmp_path: Path) -> None:
    result = _status(tmp_path, "rel/eng")
    assert result.returncode == 2
    assert "BEA_ENGINE_DIR must be an absolute path, got 'rel/eng'." in result.stderr
    assert not (tmp_path / "rel").exists()


def test_a_file_is_refused(tmp_path: Path) -> None:
    afile = tmp_path / "afile"
    afile.write_text("")
    result = _status(tmp_path, str(afile), json_output=True)
    assert result.returncode == 2
    error = json.loads(result.stderr)["error"]
    assert error["category"] == "usage"
    assert f"BEA_ENGINE_DIR points at '{afile}', which is not a directory" in error["message"]


def test_an_absolute_directory_still_works(tmp_path: Path) -> None:
    result = _status(tmp_path, str(tmp_path / "engine"))
    assert result.returncode == 0, result.stderr
    assert f"at {tmp_path / 'engine'}" in result.stdout
