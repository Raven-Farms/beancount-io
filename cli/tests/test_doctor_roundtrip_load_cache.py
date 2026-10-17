"""`doctor roundtrip` leaves no load cache for its scratch file (w5/118).

Upstream's `roundtrip` prints the ledger to `<stem>.roundtrip1<suffix>`, reads
that back through the cached loader, and removes only its two scratch files.
On a ledger slow enough to be cached, Beancount therefore also wrote
`.<stem>.roundtrip1<suffix>.picklecache` beside the ledger — about three times
the ledger's size — and nothing ever removed it. `bea` now removes it, and
leaves the ledger's own cache alone (switching the cache off for the child
would make Beancount delete that one).

Since w5/175 the default cache is kept under the `bea` cache home, so the
ledger's directory holds the ledger alone and the same holds one level over.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """option "operating_currency" "USD"
2000-01-01 open Assets:Bank USD
2000-01-01 open Expenses:Food USD
2020-01-01 * "lunch"
  Expenses:Food  1 USD
  Assets:Bank
"""

# Beancount caches a load only when it took a second. The scratch file is
# printed entries, so no ledger plugin can slow it; this makes every load in a
# child that slow without sixty thousand transactions. It leaves the cache
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


def _bea(tmp_path: Path, *args: str, slow: bool = True, pattern: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("BEA_", "BEANCOUNT_"))}
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
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _books(tmp_path: Path) -> Path:
    books = tmp_path / "books"
    books.mkdir()
    (books / "main.bean").write_text(LEDGER, encoding="utf-8")
    return books


def _listing(books: Path) -> list[str]:
    return sorted(path.name for path in books.iterdir())


def _cached(tmp_path: Path) -> list[str]:
    """What the cache home holds, each name without its directory key."""
    home = tmp_path / "cache" / "bea" / "load-cache"
    return sorted(path.name.split(".", 1)[1] for path in home.iterdir()) if home.is_dir() else []


def test_a_cached_ledger_keeps_only_its_own_cache(tmp_path: Path) -> None:
    books = _books(tmp_path)
    ledger = books / "main.bean"
    assert _bea(tmp_path, "--file", str(ledger), "check").returncode == 0
    assert _cached(tmp_path) == ["main.bean.picklecache"], "the fixture must be slow enough to be cached"
    (own_cache,) = (tmp_path / "cache" / "bea" / "load-cache").iterdir()
    before = _listing(books)
    written = own_cache.stat().st_mtime_ns

    done = _bea(tmp_path, "doctor", "roundtrip", str(ledger))

    assert done.returncode == 0, done.stderr
    assert "Entries are the same. Congratulations." in done.stderr
    assert _listing(books) == before == ["main.bean"]
    assert _cached(tmp_path) == ["main.bean.picklecache"]
    assert own_cache.stat().st_mtime_ns == written


def test_an_uncached_slow_ledger_gains_only_its_own_cache(tmp_path: Path) -> None:
    books = _books(tmp_path)

    done = _bea(tmp_path, "doctor", "roundtrip", str(books / "main.bean"))

    assert done.returncode == 0, done.stderr
    assert "Entries are the same. Congratulations." in done.stderr
    assert _listing(books) == ["main.bean"]
    assert _cached(tmp_path) == ["main.bean.picklecache"]


def test_a_symlinked_ledger_leaves_nothing_beside_its_target(tmp_path: Path) -> None:
    books = _books(tmp_path)
    link = tmp_path / "link.bean"
    link.symlink_to(books / "main.bean")

    done = _bea(tmp_path, "doctor", "roundtrip", str(link))

    assert done.returncode == 0, done.stderr
    assert _listing(books) == ["main.bean"]
    # Doctor loads the path as named, as `check` does, so the cache follows the link's name (w5/568).
    assert _cached(tmp_path) == ["link.bean.picklecache"]
    assert sorted(path.name for path in tmp_path.iterdir() if "roundtrip" in path.name) == []


def test_a_configured_cache_name_is_followed(tmp_path: Path) -> None:
    books = _books(tmp_path)

    done = _bea(tmp_path, "doctor", "roundtrip", str(books / "main.bean"), pattern="{filename}.cache")

    assert done.returncode == 0, done.stderr
    assert _listing(books) == ["main.bean", "main.bean.cache"]


def test_a_cache_name_shared_with_the_ledger_is_not_removed(tmp_path: Path) -> None:
    books = _books(tmp_path)

    done = _bea(tmp_path, "doctor", "roundtrip", str(books / "main.bean"), pattern="shared.cache")

    assert done.returncode == 0, done.stderr
    assert _listing(books) == ["main.bean", "shared.cache"]


def test_a_file_the_run_did_not_write_is_kept(tmp_path: Path) -> None:
    """Upstream refuses the stray argument before loading anything, so the name was never its own."""
    books = _books(tmp_path)
    kept = books / ".main.roundtrip1.bean.picklecache"
    kept.write_bytes(b"not this run's")

    done = _bea(tmp_path, "doctor", "roundtrip", str(books / "main.bean"), "stray.bean")

    assert done.returncode == 2, done.stderr
    assert kept.read_bytes() == b"not this run's"
    assert _listing(books) == [".main.roundtrip1.bean.picklecache", "main.bean"]


def test_a_fast_ledger_directory_is_left_as_it_was_found(tmp_path: Path) -> None:
    books = _books(tmp_path)

    done = _bea(tmp_path, "doctor", "roundtrip", str(books / "main.bean"), slow=False)

    assert done.returncode == 0, done.stderr
    assert "Entries are the same. Congratulations." in done.stderr
    assert _listing(books) == ["main.bean"]
