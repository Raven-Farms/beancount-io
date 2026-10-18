"""The update-check cache is replaced, never written through, and never waited on (w5/590).

`write_cache` used `path.write_text`, so a symlink at `update-check.json`
had its target overwritten with the cache, outside the config directory, by
every `bea upgrade --check` and every daily notice. A FIFO there hung the
command. Every other state writer already replaced the path atomically.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from cli import update

from .conftest import FakeIndex

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX links, FIFOs and modes")


def _upgrade_check(cwd: Path) -> subprocess.CompletedProcess[str]:
    # A subprocess, so a hang is a timeout rather than a stuck suite. The
    # fixtures have already pointed BEA_CONFIG_DIR and the index at tmp.
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "NO_COLOR": "1"}
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "upgrade", "--check"],
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def _assert_a_regular_cache(path: Path, version: str) -> None:
    assert stat.S_ISREG(path.lstat().st_mode)
    assert json.loads(path.read_text())["version"] == version


def test_upgrade_check_replaces_a_link_instead_of_writing_its_target(
    fake_index: FakeIndex, bea_config_dir: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    precious = outside / "precious.txt"
    precious.write_text("precious\n")
    bea_config_dir.mkdir()
    (bea_config_dir / "update-check.json").symlink_to(Path("..") / "outside" / "precious.txt")

    result = _upgrade_check(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert fake_index.requests == ["/pypi/beancount-io/json"]
    assert precious.read_text() == "precious\n"
    _assert_a_regular_cache(bea_config_dir / "update-check.json", "9.9.9")


def test_upgrade_check_answers_past_a_fifo(fake_index: FakeIndex, bea_config_dir: Path, tmp_path: Path) -> None:
    bea_config_dir.mkdir()
    os.mkfifo(bea_config_dir / "update-check.json")

    result = _upgrade_check(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "9.9.9" in result.stdout
    _assert_a_regular_cache(bea_config_dir / "update-check.json", "9.9.9")


def test_a_fifo_reads_as_not_cached(bea_config_dir: Path) -> None:
    bea_config_dir.mkdir()
    fifo = bea_config_dir / "update-check.json"
    os.mkfifo(fifo)
    answer: list[tuple[float, str] | None] = []
    reader = threading.Thread(target=lambda: answer.append(update.read_cache()), daemon=True)
    reader.start()
    reader.join(10)
    if reader.is_alive():
        # Release the blocked open, so a failure does not leave a stuck thread behind.
        os.close(os.open(fifo, os.O_WRONLY | os.O_NONBLOCK))
        reader.join(10)
        pytest.fail("reading the cache waited on a FIFO")
    assert answer == [None]


def test_the_daily_notice_replaces_a_link_too(fake_index: FakeIndex, bea_config_dir: Path, tmp_path: Path) -> None:
    precious = tmp_path / "precious.txt"
    precious.write_text("precious\n")
    bea_config_dir.mkdir()
    (bea_config_dir / "update-check.json").symlink_to(precious)

    cache_file = update._writable_cache("pypi")
    assert update.latest_version(cache_file=cache_file) == "9.9.9"

    assert precious.read_text() == "precious\n"
    _assert_a_regular_cache(bea_config_dir / "update-check.json", "9.9.9")


@pytest.mark.skipif(os.geteuid() == 0, reason="root writes into a mode-500 directory")
def test_a_writable_cache_in_a_read_only_directory_is_remembered_elsewhere(
    fake_index: FakeIndex, bea_config_dir: Path, tmp_path: Path
) -> None:
    """A replace needs the directory, so the outcome goes to the cache directory (w5/321)."""
    bea_config_dir.mkdir()
    stale = bea_config_dir / "update-check.json"
    stale.write_text(json.dumps({"checked_at": 0.0, "version": "1.0.0"}))
    bea_config_dir.chmod(0o500)
    try:
        for _ in range(2):
            assert update.latest_version(cache_file=update._writable_cache("pypi")) == "9.9.9"
    finally:
        bea_config_dir.chmod(stat.S_IRWXU)

    assert fake_index.requests == ["/pypi/beancount-io/json"]
    _assert_a_regular_cache(tmp_path / "xdg-cache" / "bea" / "update-check.json", "9.9.9")
