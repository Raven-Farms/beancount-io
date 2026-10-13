"""A read leaves no copy of the ledger beside it (w5/175).

Beancount caches a load that took a second in `.<name>.picklecache` beside the
file it read: every directive again, created with the process umask. For books
kept `0600` that was a `0644` copy under the common umask and `0666` under
none; a link already at that name was written through, and a file already
there was unpickled and believed by the next read. `bea` now keeps the cache
under its cache home, in a directory only its owner can enter.
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """option "operating_currency" "USD"
2000-01-01 open Assets:Bank USD
2000-01-01 open Expenses:Food USD
2020-01-01 * "lunch"
  Expenses:Food  1 USD
  Assets:Bank
2020-01-02 note Assets:Bank "{word}"
"""

# Beancount caches a load only when it took a second. This makes every load in
# a child that slow without sixty thousand transactions, and leaves the cache
# decision itself — `loader.initialize` and its threshold — exactly as shipped.
SLOW_LOADS = """\
import time

try:
    from beancount import loader
except ImportError:
    pass
else:
    _load = loader._load

    def _slow_load(*args, **kwargs):
        time.sleep(1.05)
        return _load(*args, **kwargs)

    loader._load = _slow_load
"""

READS = [
    ["--file", "main.bean", "list", "note"],
    ["--file", "main.bean", "check"],
    ["--file", "main.bean", "balance"],
    ["doctor", "missing-open", "main.bean"],
]
READ_IDS = ["list", "check", "balance", "doctor"]


def _env(tmp_path: Path, *, slow: bool = True, pattern: str | None = None) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("BEA_", "BEANCOUNT_")) and k != "CI"}
    search = [str(ROOT / "src")]
    if slow:
        site = tmp_path / "site"
        site.mkdir(exist_ok=True)
        (site / "sitecustomize.py").write_text(SLOW_LOADS, encoding="utf-8")
        search.append(str(site))
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=os.pathsep.join(search),
        TERM="dumb",
        NO_COLOR="1",
    )
    if pattern is not None:
        env["BEANCOUNT_LOAD_CACHE_FILENAME"] = pattern
    return env


def _bea(
    tmp_path: Path, *args: str, umask: int = 0o022, slow: bool = True, pattern: str | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=_env(tmp_path, slow=slow, pattern=pattern),
        cwd=tmp_path / "books",
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        umask=umask,
    )


def _books(tmp_path: Path, word: str = "genuine") -> Path:
    books = tmp_path / "books"
    books.mkdir()
    ledger = books / "main.bean"
    ledger.write_text(LEDGER.format(word=word), encoding="utf-8")
    ledger.chmod(0o600)
    return books


def _listing(directory: Path) -> list[str]:
    return sorted(path.name for path in directory.iterdir())


def _caches(tmp_path: Path) -> list[Path]:
    home = tmp_path / "cache" / "bea" / "load-cache"
    return sorted(home.iterdir()) if home.is_dir() else []


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission bits")
@pytest.mark.parametrize("umask", [0o022, 0o000], ids=["umask-022", "umask-000"])
@pytest.mark.parametrize("read", READS, ids=READ_IDS)
def test_a_slow_read_leaves_the_ledger_directory_as_it_found_it(tmp_path: Path, read: list[str], umask: int) -> None:
    books = _books(tmp_path)

    done = _bea(tmp_path, *read, umask=umask)

    assert done.returncode == 0, done.stderr
    assert _listing(books) == ["main.bean"]
    (cache,) = _caches(tmp_path)
    assert cache.name.endswith(".main.bean.picklecache"), "the fixture must be slow enough to be cached"
    assert stat.S_IMODE(cache.parent.stat().st_mode) == 0o700, "the copy is reachable by its owner alone"
    assert stat.S_IMODE((books / "main.bean").stat().st_mode) == 0o600


def test_a_second_read_is_answered_from_the_cache_and_a_changed_ledger_is_read_again(tmp_path: Path) -> None:
    books = _books(tmp_path)
    first = _bea(tmp_path, "--file", "main.bean", "list", "note")
    assert first.returncode == 0, first.stderr
    assert "genuine" in first.stdout
    (cache,) = _caches(tmp_path)
    written = cache.stat().st_mtime_ns

    second = _bea(tmp_path, "--file", "main.bean", "list", "note")

    assert second.returncode == 0, second.stderr
    assert second.stdout == first.stdout
    assert cache.stat().st_mtime_ns == written, "a clean hit must stay a hit"

    with (books / "main.bean").open("a", encoding="utf-8") as stream:
        stream.write('2020-01-03 note Assets:Bank "appended"\n')
    third = _bea(tmp_path, "--file", "main.bean", "list", "note")

    assert third.returncode == 0, third.stderr
    assert "appended" in third.stdout
    assert _listing(books) == ["main.bean"]


def test_two_ledgers_of_one_name_keep_separate_caches(tmp_path: Path) -> None:
    books = _books(tmp_path)
    other = books / "other"
    other.mkdir()
    (other / "main.bean").write_text(LEDGER.format(word="elsewhere"), encoding="utf-8")

    here = _bea(tmp_path, "--file", "main.bean", "list", "note")
    there = _bea(tmp_path, "--file", "other/main.bean", "list", "note")

    assert "genuine" in here.stdout
    assert "elsewhere" in there.stdout
    assert "genuine" not in there.stdout
    assert len(_caches(tmp_path)) == 2


def test_a_link_at_the_old_cache_name_is_not_written_through(tmp_path: Path) -> None:
    books = _books(tmp_path)
    target = tmp_path / "outside" / "copy.pickle"
    target.parent.mkdir()
    (books / ".main.bean.picklecache").symlink_to(target)

    done = _bea(tmp_path, "--file", "main.bean", "list", "note")

    assert done.returncode == 0, done.stderr
    assert _listing(target.parent) == [], "the ledger's contents were written outside its directory"
    assert (books / ".main.bean.picklecache").is_symlink(), "not this command's to remove"


def test_a_cache_file_found_beside_the_ledger_does_not_supply_the_answer(tmp_path: Path) -> None:
    """A folder obtained from elsewhere can carry a cache upstream would trust."""
    books = _books(tmp_path, word="planted")
    ledger = books / "main.bean"
    planted = subprocess.run(
        [sys.executable, "-c", "from beancount import loader; loader.load_file('main.bean')"],
        env=_env(tmp_path),
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert planted.returncode == 0, planted.stderr
    assert _listing(books) == [".main.bean.picklecache", "main.bean"], "upstream's own cache is the precondition"
    # Same size and timestamp, so the planted cache still looks fresh to upstream.
    before = ledger.stat()
    ledger.write_text(LEDGER.format(word="genuine"), encoding="utf-8")
    os.utime(ledger, ns=(before.st_atime_ns, before.st_mtime_ns))
    assert ledger.stat().st_size == before.st_size

    done = _bea(tmp_path, "--file", "main.bean", "list", "note")

    assert done.returncode == 0, done.stderr
    assert "genuine" in done.stdout
    assert "planted" not in done.stdout


def test_a_fast_read_writes_no_cache_anywhere(tmp_path: Path) -> None:
    """The control: a load under a second was never cached, and still is not."""
    books = _books(tmp_path)

    done = _bea(tmp_path, "--file", "main.bean", "list", "note", slow=False)

    assert done.returncode == 0, done.stderr
    assert _listing(books) == ["main.bean"]
    assert _caches(tmp_path) == []


@pytest.mark.parametrize("read", READS[:2], ids=READ_IDS[:2])
def test_a_cache_location_the_user_chose_is_still_followed(tmp_path: Path, read: list[str]) -> None:
    """The control: `BEANCOUNT_LOAD_CACHE_FILENAME` keeps upstream's meaning."""
    books = _books(tmp_path)

    done = _bea(tmp_path, *read, pattern="{filename}.cache")

    assert done.returncode == 0, done.stderr
    assert _listing(books) == ["main.bean", "main.bean.cache"]
    assert _caches(tmp_path) == []
