"""The staging sweep removes `bea`'s own abandoned copies and nothing else (w5/173).

Before each write the ledger's directory is swept for staging copies a killed
write left behind. The sweep matched any old regular file named `.bea-*` or
`..bea-*`, so a user's `.bea-rules.yaml` beside the books was deleted silently
— also by a write that was refused with "nothing was written".

w5/719 extends the sweep: a candidate whose writer is alive stays locked
(POSIX) or open (Windows), so the test's simulated in-flight file is held
for the run; an unlocked one is an orphan however young and goes at once.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from bea_engine.ledger.write import pickle_cache_of, sweep_abandoned_candidates

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """\
option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Equity:Open USD
2026-01-02 * "o"
  Assets:Checking  1 USD
  Equity:Open
"""

USER_FILES = [".bea-rules.yaml", ".bea-notes.md", "..bea-thing", ".beanotes.txt"]
CANDIDATE = ".bea-0123456789abcdef.tmp"
SIDECAR = f".{CANDIDATE}.picklecache"
IN_FLIGHT = ".bea-fedcba9876543210.tmp"
FRESH_ORPHAN = ".bea-aaaaaaaaaaaaaaaa.tmp"

WRITES = {
    "add": (["add", "note", "-a", "Assets:Checking", "--date", "2026-05-02", "-m", "n"], 0, "Added 1 note"),
    "refused-add": (["add", "note", "-a", "Assets:Nope", "--date", "2026-05-02", "-m", "n"], 1, "nothing was written"),
    "format": (["format", "-i"], 0, "0/1 file(s) formatted."),
}


def _aged(path: Path) -> Path:
    path.write_text("mine\n", encoding="utf-8")
    old = time.time() - 40 * 86400
    os.utime(path, (old, old))
    return path


def _books(tmp_path: Path) -> Path:
    books = tmp_path / "books"
    books.mkdir()
    (books / "main.bean").write_text(LEDGER, encoding="utf-8")
    for name in (*USER_FILES, CANDIDATE, SIDECAR):
        _aged(books / name)
    (books / IN_FLIGHT).write_text("staged\n", encoding="utf-8")
    (books / FRESH_ORPHAN).write_text("staged\n", encoding="utf-8")
    return books


@contextmanager
def _held(path: Path) -> Iterator[None]:
    """Hold a candidate the way its writer would, on any platform (w5/719)."""
    if sys.platform == "win32":
        with open(path, "rb"):
            yield
    else:
        import fcntl

        fd = os.open(path, os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)


def _bea(tmp_path: Path, books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
        COLUMNS="200",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", "main.bean", *args],
        cwd=books,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _names(books: Path) -> set[str]:
    return {path.name for path in books.iterdir()}


@pytest.mark.parametrize("write", sorted(WRITES))
def test_a_write_leaves_the_users_own_dotfiles_beside_the_ledger(tmp_path: Path, write: str) -> None:
    args, status, said = WRITES[write]
    books = _books(tmp_path)

    with _held(books / IN_FLIGHT):
        result = _bea(tmp_path, books, *args)

    assert result.returncode == status, result.stderr
    assert said in " ".join((result.stdout + result.stderr).split())
    assert _names(books) == {"main.bean", *USER_FILES, IN_FLIGHT}
    assert all((books / name).read_text(encoding="utf-8") == "mine\n" for name in USER_FILES)


def test_a_read_sweeps_nothing(tmp_path: Path) -> None:
    """The control: only a write tidies up, so a read leaves even a real orphan."""
    books = _books(tmp_path)
    before = _names(books)

    assert _bea(tmp_path, books, "check").returncode == 0
    assert _bea(tmp_path, books, "list", "open").returncode == 0

    assert _names(books) == before


@pytest.mark.parametrize(
    "name",
    [
        *USER_FILES,
        ".bea-0123456789abcdef.tmp.bak",
        ".bea-0123456789abcdef.tmp.picklecache",
        ".bea-0123456789ABCDEF.tmp",
        ".bea-0123456789abcde.tmp",
        ".bea-0123456789abcdef0.tmp",
        "..bea-0123456789abcdef.tmp",
        "..bea-0123456789abcdef.tmp.picklecache.bak",
        "...bea-0123456789abcdef.tmp.picklecache",
    ],
)
def test_the_sweep_ignores_a_name_bea_never_generates(tmp_path: Path, name: str) -> None:
    near_miss = _aged(tmp_path / name)

    sweep_abandoned_candidates(tmp_path)

    assert near_miss.exists()


def test_the_sweep_still_takes_a_candidate_and_the_sidecar_beancount_names(tmp_path: Path) -> None:
    """Both places a candidate's load cache can be.

    Beside it, under Beancount's own name: what versions before w5/175 left,
    and what a relative `BEANCOUNT_LOAD_CACHE_FILENAME` still produces. And
    under the `bea` cache home, where the default cache is kept now.
    """
    candidate = _aged(tmp_path / CANDIDATE)
    sidecar = _aged(tmp_path / SIDECAR)
    relocated = pickle_cache_of(candidate)
    assert relocated.name.endswith(SIDECAR)
    assert relocated.parent != tmp_path
    _aged(relocated)

    sweep_abandoned_candidates(tmp_path)

    assert not candidate.exists()
    assert not relocated.exists()
    assert not sidecar.exists()
