"""Provisioning never deletes a directory bea did not build (w5/419).

`BEA_ENGINE_DIR` is taken as given, and a rebuild replaces the root and
deletes what was there: a typo naming a data folder would have been deleted
once the install succeeded. `uv` is a shell stub that lays out the files
`is_provisioned` looks for, so no network is involved.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_engine_provision_races import PROVISION, SOURCE_ROOT, fake_uv  # noqa: F401

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="the fake uv is a POSIX shell script")


def _provision(fake_uv: Path, tmp_path: Path, engine: Path | None) -> subprocess.CompletedProcess[str]:  # noqa: F811
    env = {key: value for key, value in os.environ.items() if not key.startswith("BEA_")}
    env.update(BEA_UV=str(fake_uv), PYTHONPATH=str(SOURCE_ROOT), XDG_DATA_HOME=str(tmp_path / "data"))
    if engine is not None:
        env["BEA_ENGINE_DIR"] = str(engine)
    return subprocess.run(
        [sys.executable, "-c", PROVISION], env=env, capture_output=True, text=True, timeout=120, check=False
    )


def test_a_data_folder_is_refused_and_kept(fake_uv: Path, tmp_path: Path) -> None:  # noqa: F811
    books = tmp_path / "books"
    books.mkdir()
    (books / "main.bean").write_text("2026-01-01 open Assets:Cash\n")

    result = _provision(fake_uv, tmp_path, books)

    assert result.returncode != 0
    assert f"BEA_ENGINE_DIR points at '{books}', which holds files but no engine bea built" in result.stderr
    assert (books / "main.bean").read_text() == "2026-01-01 open Assets:Cash\n"
    # The provisioning lock always sits beside the root; no build was started or moved anything aside.
    assert sorted(path.name for path in tmp_path.iterdir() if path.name.startswith("books")) == ["books", "books.lock"]


def test_a_file_is_refused(fake_uv: Path, tmp_path: Path) -> None:  # noqa: F811
    target = tmp_path / "engine"
    target.write_text("keep\n")
    result = _provision(fake_uv, tmp_path, target)
    assert result.returncode != 0
    assert "which is not a directory" in result.stderr
    assert target.read_text() == "keep\n"


@pytest.mark.parametrize("state", ["missing", "empty", "marked-damaged"])
def test_bea_directories_are_still_built_or_repaired(fake_uv: Path, tmp_path: Path, state: str) -> None:  # noqa: F811
    engine = tmp_path / "engine"
    if state != "missing":
        engine.mkdir()
    if state == "marked-damaged":
        (engine / ".bea-engine").write_text("bea engine 0.0.0\n")
        (engine / "stale.txt").write_text("from a broken build\n")

    result = _provision(fake_uv, tmp_path, engine)

    assert result.returncode == 0, result.stderr
    assert (engine / ".bea-engine").is_file()
    assert not (engine / "stale.txt").exists()


def test_the_default_location_still_repairs_an_engine_from_before_the_marker(
    fake_uv: Path,  # noqa: F811
    tmp_path: Path,
) -> None:
    result = _provision(fake_uv, tmp_path, None)
    assert result.returncode == 0, result.stderr
    engine = Path(result.stdout.strip()).parent.parent
    (engine / ".bea-engine").unlink()
    (engine / "bin" / "python").unlink()

    repaired = _provision(fake_uv, tmp_path, None)

    assert repaired.returncode == 0, repaired.stderr
    assert (engine / "bin" / "python").exists() and (engine / ".bea-engine").is_file()
