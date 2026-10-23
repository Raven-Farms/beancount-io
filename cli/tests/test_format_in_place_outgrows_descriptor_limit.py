"""`format -i DIR` is not bounded by the open-file limit (w5/207).

In-place formatting takes every target's lock before it writes the first
byte, and each lock is an open descriptor. Under macOS's default soft limit of
256 a directory of 260 files therefore could not be formatted at all: the run
stopped on "Too many open files", blamed the lock directory, and listed every
file as not attempted.

The limit is lowered with `RLIMIT_NOFILE` on the child, so the failure is the
kernel's own EMFILE rather than a mock. Two shapes of it matter: a soft limit
the engine may raise, and a hard limit it may not, where it has to lock one
file at a time instead.
"""

from __future__ import annotations

import json
import os
import resource
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from bea_engine.ledger import formatting
from bea_engine.ledger import write as ledger_write

ROOT = Path(__file__).resolve().parents[1]
BEA = ROOT / ".venv" / "bin" / "bea"

# The note's fixture: the amount columns are ragged, so every file is rewritten.
MISALIGNED = '2020-01-01 open Assets:Bank USD\n2020-01-02 * "t"\n  Assets:Bank      1 USD\n  Assets:Bank  -1 USD\n'
LIMIT = 256


def _env(tmp_path: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        TERM="dumb",
        NO_COLOR="1",
    )
    return env


def _soft_limit() -> None:  # pragma: no cover - runs in the forked child
    resource.setrlimit(resource.RLIMIT_NOFILE, (LIMIT, resource.getrlimit(resource.RLIMIT_NOFILE)[1]))


def _hard_limit() -> None:  # pragma: no cover - runs in the forked child
    resource.setrlimit(resource.RLIMIT_NOFILE, (LIMIT, LIMIT))


LIMITS = {"soft": _soft_limit, "hard": _hard_limit}


def _books(tmp_path: Path, files: int) -> Path:
    books = tmp_path / "books"
    books.mkdir()
    for index in range(files):
        (books / f"f{index:04d}.bean").write_text(MISALIGNED, encoding="utf-8")
    return books


def _format_in_place(tmp_path: Path, books: Path, *prefix: str, limit: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(BEA), *prefix, "format", "-i", str(books)],
        env=_env(tmp_path),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
        preexec_fn=LIMITS[limit],
    )


def _all_formatted(books: Path) -> bool:
    return all(path.read_text(encoding="utf-8") != MISALIGNED for path in books.iterdir())


@pytest.mark.parametrize("limit", ["soft", "hard"])
def test_more_files_than_the_descriptor_limit_are_all_formatted(tmp_path: Path, limit: str) -> None:
    books = _books(tmp_path, files=LIMIT + 4)

    done = _format_in_place(tmp_path, books, limit=limit)

    assert done.returncode == 0, done.stderr[:2000]
    assert done.stderr == ""
    assert f"{LIMIT + 4}/{LIMIT + 4} file(s) formatted." in done.stdout
    assert _all_formatted(books)
    assert sorted(path.name for path in books.iterdir()) == [f"f{index:04d}.bean" for index in range(LIMIT + 4)]


def test_json_reports_every_file_formatted_past_the_limit(tmp_path: Path) -> None:
    books = _books(tmp_path, files=LIMIT + 4)

    done = _format_in_place(tmp_path, books, "--json", limit="hard")

    assert done.returncode == 0, done.stderr[:2000]
    data = json.loads(done.stdout)["data"]
    assert data["formatted"] == sorted(str(path.resolve()) for path in books.iterdir())
    assert data["failed"] == []
    assert _all_formatted(books)


@pytest.mark.parametrize("limit", ["soft", "hard"])
def test_a_directory_within_the_limit_still_formats(tmp_path: Path, limit: str) -> None:
    """The control: this many files fitted before, and still does."""
    books = _books(tmp_path, files=40)

    done = _format_in_place(tmp_path, books, limit=limit)

    assert done.returncode == 0, done.stderr[:2000]
    assert "40/40 file(s) formatted." in done.stdout
    assert _all_formatted(books)


def test_past_the_hard_limit_each_file_is_rewritten_under_its_own_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One lock at a time is still a lock: no file is replaced outside its own."""
    files = sorted(_books(tmp_path, files=5).resolve().iterdir())
    held: list[Path] = []
    most_held = 0
    replaced_under: dict[Path, list[Path]] = {}
    real_lock = ledger_write.lock_file
    real_replace = ledger_write.replace_checked

    @contextmanager
    def recording_lock(file: Path) -> Iterator[None]:
        nonlocal most_held
        with real_lock(file):
            held.append(file)
            most_held = max(most_held, len(held))
            try:
                yield
            finally:
                held.remove(file)

    def recording_replace(file: Path, candidate: Path, original: bytes, original_stat: os.stat_result) -> None:
        replaced_under[file] = list(held)
        real_replace(file, candidate, original, original_stat)

    monkeypatch.setattr(ledger_write, "descriptors_allow", lambda locks: False)
    monkeypatch.setattr(ledger_write, "lock_file", recording_lock)
    monkeypatch.setattr(ledger_write, "replace_checked", recording_replace)

    result = formatting.format_files(files, in_place=True, prefix_width=None, num_width=None, currency_column=None)

    assert result == {"changed": [str(file) for file in files]}
    assert replaced_under == {file: [file] for file in files}
    assert most_held == 1
    assert held == []


def test_within_the_limit_every_lock_is_still_taken_before_the_first_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control for the fallback: a run that fits keeps its all-locks-first order."""
    files = sorted(_books(tmp_path, files=5).resolve().iterdir())
    held: list[Path] = []
    replaced_under: list[int] = []
    real_lock = ledger_write.lock_file
    real_replace = ledger_write.replace_checked

    @contextmanager
    def recording_lock(file: Path) -> Iterator[None]:
        with real_lock(file):
            held.append(file)
            yield

    def recording_replace(file: Path, candidate: Path, original: bytes, original_stat: os.stat_result) -> None:
        replaced_under.append(len(held))
        real_replace(file, candidate, original, original_stat)

    monkeypatch.setattr(ledger_write, "lock_file", recording_lock)
    monkeypatch.setattr(ledger_write, "replace_checked", recording_replace)

    formatting.format_files(files, in_place=True, prefix_width=None, num_width=None, currency_column=None)

    assert replaced_under == [5] * 5
