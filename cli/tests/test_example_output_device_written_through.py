"""`bea example -o` writes through a device or FIFO instead of refusing it (w5/277).

The one destination rule says a device or FIFO is written through rather than
replaced. `example` saw `/dev/null` as an existing file and demanded `--force`
with exit 4, though there is nothing there to overwrite.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

RANGE = ["--seed", "1", "--date-begin", "2026-01-01", "--date-end", "2026-04-01"]


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.mark.skipif(not Path("/dev/null").is_char_device(), reason="needs /dev/null")
def test_dev_null_is_written_through_without_force(tmp_path: Path) -> None:
    result = _bea(tmp_path, "example", *RANGE, "-o", "/dev/null")

    assert result.returncode == 0, result.stderr
    assert "Already exists" not in result.stderr
    assert result.stdout == ""
    assert Path("/dev/null").is_char_device()


@pytest.mark.skipif(not Path("/dev/null").is_char_device(), reason="needs /dev/null")
def test_symlink_to_a_device_is_written_through(tmp_path: Path) -> None:
    link = tmp_path / "sink.bean"
    link.symlink_to("/dev/null")

    result = _bea(tmp_path, "example", *RANGE, "-o", str(link))

    assert result.returncode == 0, result.stderr
    assert link.is_symlink()


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="needs FIFOs")
def test_fifo_receives_the_generated_ledger(tmp_path: Path) -> None:
    fifo = tmp_path / "pipe.bean"
    os.mkfifo(fifo)
    received: list[str] = []
    reader = threading.Thread(target=lambda: received.append(fifo.read_text(encoding="utf-8")), daemon=True)
    reader.start()

    result = _bea(tmp_path, "example", *RANGE, "-o", str(fifo))
    if result.returncode != 0:
        # Release the reader, which otherwise waits for a writer that never came.
        with fifo.open("w", encoding="utf-8"):
            pass
    reader.join(timeout=30)

    assert result.returncode == 0, result.stderr
    assert "Assets:US:BofA:Checking" in received[0]
    assert fifo.is_fifo()


def test_existing_regular_file_is_still_a_conflict(tmp_path: Path) -> None:
    victim = tmp_path / "books.bean"
    victim.write_text("; mine\n", encoding="utf-8")
    link = tmp_path / "link.bean"
    link.symlink_to(victim)

    for target in (victim, link):
        result = _bea(tmp_path, "example", *RANGE, "-o", str(target))
        assert result.returncode == 4, result.stderr
        assert "Already exists" in result.stderr
    assert victim.read_text(encoding="utf-8") == "; mine\n"


def test_existing_directory_and_dangling_symlink_are_still_conflicts(tmp_path: Path) -> None:
    directory = tmp_path / "out"
    directory.mkdir()
    dangling = tmp_path / "dangling.bean"
    dangling.symlink_to(tmp_path / "missing.bean")

    for target in (directory, dangling):
        result = _bea(tmp_path, "example", *RANGE, "-o", str(target))
        assert result.returncode == 4, result.stderr
        assert "Already exists" in result.stderr
    assert not (tmp_path / "missing.bean").exists()
