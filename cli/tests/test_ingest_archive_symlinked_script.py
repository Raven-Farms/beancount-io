"""`ingest archive` files beside a symlinked ingest script, not beside its target (w5/166).

Beangulp's default archive destination is the directory of the script path it
was started with. `bea ingest` dereferenced a symlinked `ingest.py` before
spawning it, so the statements were moved into the shared script's directory
instead of the books'.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_ingest import INGEST_SCRIPT

ROOT = Path(__file__).resolve().parents[1]
ARCHIVED = Path("Assets", "Tests", "1970-01-01.a.csv")


def _archive(root: Path, engine: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(root / "config"),
        XDG_CACHE_HOME=str(root / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_ENGINE_PYTHON=str(engine),
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--file", "books/main.bean", "ingest", "archive", *args, "books/dl"],
        cwd=root,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _books(root: Path, *, symlinked: bool) -> Path:
    books = root / "books"
    (books / "dl").mkdir(parents=True)
    (books / "dl" / "a.csv").write_text("Date,Payee,Narration,Amount\n2026-08-02,Cafe,Coffee,-5.25\n")
    (books / "main.bean").write_text('option "operating_currency" "USD"\n2026-01-01 open Assets:Tests USD\n')
    if symlinked:
        shared = root / "shared"
        shared.mkdir()
        (shared / "ingest.py").write_text(INGEST_SCRIPT)
        (books / "ingest.py").symlink_to(Path("..", "shared", "ingest.py"))
    else:
        (books / "ingest.py").write_text(INGEST_SCRIPT)
    return books


@pytest.mark.skipif(sys.platform == "win32", reason="needs an unprivileged symlink")
@pytest.mark.parametrize("config", [["--config", "books/ingest.py"], []], ids=["explicit-config", "beside-ledger"])
def test_archive_files_beside_the_symlink_not_its_target(
    tmp_path: Path, use_optional_engine: Path, config: list[str]
) -> None:
    books = _books(tmp_path, symlinked=True)

    result = _archive(tmp_path, use_optional_engine, *config)

    assert result.returncode == 0, result.stderr
    assert (books / ARCHIVED).is_file()
    assert not (books / "dl" / "a.csv").exists()
    assert not (tmp_path / "shared" / "Assets").exists()
    assert (books / "ingest.py").is_symlink()


@pytest.mark.parametrize("config", [["--config", "books/ingest.py"], []], ids=["explicit-config", "beside-ledger"])
def test_archive_beside_a_regular_script_is_unchanged(
    tmp_path: Path, use_optional_engine: Path, config: list[str]
) -> None:
    books = _books(tmp_path, symlinked=False)

    result = _archive(tmp_path, use_optional_engine, *config)

    assert result.returncode == 0, result.stderr
    assert (books / ARCHIVED).is_file()
    assert not (books / "dl" / "a.csv").exists()
