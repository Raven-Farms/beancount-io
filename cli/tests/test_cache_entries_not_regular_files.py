"""A cache entry of bea's own that is not a regular file never breaks or hangs a read (w5/591).

The regular-file guard on the load cache (w5/417, w5/418) ran only for a path
the user set. At bea's private default, a directory crashed `bea check` with
bean-check's traceback and every other read with `IsADirectoryError`, and a
FIFO hung them. A FIFO in the managed-price cache (`head.json`, a revision,
its sidecar or an effective file) hung every read, `--offline` included.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_price import _run_bea, _write_managed_ledger
from tests.test_price import feed_server as feed_server  # noqa: F401 - the fixture

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """\
2026-01-01 open Assets:Cash
2026-01-01 open Equity:Opening
2026-01-02 * "opening"
  Assets:Cash  1 USD
  Equity:Opening
"""

pytestmark = pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX file types")


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("BEA_", "BEANCOUNT_")) and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    # The timeout is the hang detector: before the fix a FIFO never returned.
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--file", str(tmp_path / "main.bean"), *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def _private_load_cache(tmp_path: Path, text: str = LEDGER) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(text)
    digest = hashlib.sha256(os.fsencode(os.path.dirname(os.path.realpath(ledger)))).hexdigest()[:32]
    directory = tmp_path / "cache" / "bea" / "load-cache"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    return directory / f"{digest}.main.bean.picklecache"


COMMANDS = {"check": ["check"], "json-check": ["--json", "check"], "balance": ["balance"]}


@pytest.mark.parametrize("command", sorted(COMMANDS))
@pytest.mark.parametrize("kind", ["directory", "fifo"])
def test_a_stray_entry_at_the_private_load_cache_is_cleared(tmp_path: Path, kind: str, command: str) -> None:
    cache = _private_load_cache(tmp_path)
    if kind == "directory":
        cache.mkdir(mode=0o700)
    else:
        os.mkfifo(cache)

    result = _bea(tmp_path, *COMMANDS[command])

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Traceback" not in result.stderr
    assert "Error" not in result.stderr
    # Cleared, or replaced by a real cache if this load was slow enough to leave one.
    assert not os.path.lexists(cache) or cache.is_file()


@pytest.mark.parametrize("command", ["check", "balance"])
def test_a_directory_that_cannot_be_cleared_is_bypassed_and_kept(tmp_path: Path, command: str) -> None:
    cache = _private_load_cache(tmp_path)
    cache.mkdir(mode=0o700)
    (cache / "keep.txt").write_text("not bea's to delete\n")

    result = _bea(tmp_path, command)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Traceback" not in result.stderr
    assert "Error" not in result.stderr
    assert (cache / "keep.txt").read_text() == "not bea's to delete\n"


@pytest.mark.parametrize("entry", ["head.json", "r1.beancount", "r1.json", "r1.effective."])
def test_a_fifo_in_the_managed_price_cache_reads_as_missing(feed_server: str, tmp_path: Path, entry: str) -> None:
    ledger = _write_managed_ledger(tmp_path, feed_server)
    seeded = _run_bea(tmp_path, feed_server, "--file", str(ledger), "check")
    assert seeded.returncode == 0, seeded.stderr
    (directory,) = (tmp_path / "cache" / "bea" / "managed-prices").iterdir()
    (target,) = directory.glob(f"{entry}*")

    for args in (["--offline", "price", "status"], ["--offline", "balance"], ["balance"], ["check"]):
        target.unlink(missing_ok=True)
        absent = _run_bea(tmp_path, feed_server, "--file", str(ledger), *args)
        target.unlink(missing_ok=True)
        os.mkfifo(target)

        result = _run_bea(tmp_path, feed_server, "--file", str(ledger), *args)

        # Exactly what a missing entry gets: a refetch online, "no cached revision" offline.
        assert result.returncode == absent.returncode, f"{args}: {result.stdout}{result.stderr}"
        assert result.stderr == absent.stderr
        assert "Traceback" not in result.stderr


def test_a_fifo_at_the_managed_load_cache_reads_as_missing(feed_server: str, tmp_path: Path) -> None:
    """The cache of a whole managed load (w5/576) sits beside the private load cache."""
    ledger = _write_managed_ledger(tmp_path, feed_server)
    managed = Path(f"{_private_load_cache(tmp_path, ledger.read_text())}.managed")
    os.mkfifo(managed)

    for args in (["balance"], ["--offline", "balance"], ["check"]):
        result = _run_bea(tmp_path, feed_server, "--file", str(ledger), *args)

        assert result.returncode == 0, f"{args}: {result.stdout}{result.stderr}"
        assert "Traceback" not in result.stderr


@pytest.mark.parametrize("kind", ["fifo", "full-directory"])
def test_bean_doctor_gets_a_usable_load_cache_path(tmp_path: Path, kind: str) -> None:
    """`bean-doctor` is handed the private path as a pattern, and opens it unguarded."""
    cache = _private_load_cache(tmp_path)
    if kind == "fifo":
        os.mkfifo(cache)
    else:
        cache.mkdir(mode=0o700)
        (cache / "keep.txt").write_text("kept\n")

    result = _bea(tmp_path, "doctor", "display-context", str(tmp_path / "main.bean"))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "IsADirectoryError" not in result.stderr
    assert kind == "fifo" or (cache / "keep.txt").exists()
