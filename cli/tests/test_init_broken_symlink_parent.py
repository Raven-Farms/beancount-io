"""`bea init` through a dangling symlink names the broken link (w5/580).

The blocker search followed links with `exists()`, so a link to an unmounted
drive was skipped and the working directory it sat in was blamed as "a file,
not a directory".
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _init(cwd: Path, target: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(cwd / ".config"),
        XDG_CACHE_HOME=str(cwd / ".cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "init", target, "--currency", "USD", "--date", "2026-01-01"],
        env=env,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_a_dangling_link_is_named_as_broken(tmp_path: Path) -> None:
    (tmp_path / "books").symlink_to(tmp_path / "unmounted" / "books")

    result = _init(tmp_path, "books")

    assert result.returncode == 2, result.stdout + result.stderr
    message = " ".join(result.stderr.split())
    assert f"{tmp_path / 'books'} is a broken symbolic link to {tmp_path / 'unmounted' / 'books'}" in message
    assert "is a file, not a directory" not in message
    assert not (tmp_path / "unmounted").exists()


def test_a_regular_file_is_still_named_as_a_file(tmp_path: Path) -> None:
    (tmp_path / "books").write_text("not a folder\n")

    result = _init(tmp_path, "books/2026")

    assert result.returncode == 2, result.stdout + result.stderr
    assert f"{tmp_path / 'books'} is a file, not a directory" in " ".join(result.stderr.split())
