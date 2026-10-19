"""bea works whatever `PYTHONIOENCODING` the parent exports (w5/724).

The helper environment inherited the parent's codec, so under `utf-16` the
engine probe read gibberish and called a healthy managed engine damaged,
advising the user to delete it; the frontend's own error then printed
spaced-out in UTF-16 too.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _bea(tmp_path: Path, *args: str, encoding: str) -> subprocess.CompletedProcess[bytes]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "PYTHONIOENCODING"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        PYTHONIOENCODING=encoding,
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize("encoding", ["utf-16", "utf-32", "cp037"])
def test_helper_env_pins_utf8_output(monkeypatch: pytest.MonkeyPatch, encoding: str) -> None:
    from cli.engine.launch import _helper_env

    monkeypatch.setenv("PYTHONIOENCODING", encoding)

    child = _helper_env(ROOT / "src")

    assert child is not None
    assert child["PYTHONIOENCODING"] == "utf-8"


def test_probe_loads_despite_inherited_utf16(monkeypatch: pytest.MonkeyPatch) -> None:
    from cli.engine.launch import engine_load_failure

    monkeypatch.setenv("PYTHONIOENCODING", "utf-16")

    assert engine_load_failure(Path(sys.executable)) is None


def test_error_output_ignores_inherited_utf16(tmp_path: Path) -> None:
    result = _bea(tmp_path, "-f", str(tmp_path / "missing.bean"), "list", "transaction", encoding="utf-16")

    assert result.returncode == 2, result.returncode
    assert result.stderr.startswith(b"Error: ")
    assert b"\x00" not in result.stderr


def test_engine_status_reads_utf8_despite_inherited_utf16(tmp_path: Path) -> None:
    result = _bea(tmp_path, "engine", "status", encoding="utf-16")

    assert result.returncode == 0, result.stderr
    shown = result.stdout.decode("utf-8")
    assert "Serving from:" in shown
    assert "damaged" not in shown
