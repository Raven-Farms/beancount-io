"""A failed `bea format -o FILE` write leaves the previous export intact (w5/156).

`format -o` wrote the destination in place, so a write that failed part-way
replaced an existing export with a fragment ending mid-directive, and left a
partial file where none had been. It now goes through the frontend's
`atomic_write`, as `query -o` and `treeify -o` do: staged beside the
destination and swapped in only once every byte is down.

The failure is induced with `RLIMIT_FSIZE` on the child, as in
`test_export_write_is_atomic.py`: a genuine os-level write failure (EFBIG)
after formatting has succeeded, not a mock — and not a disk-full event.
"""

from __future__ import annotations

import os
import resource
import signal
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BEA = ROOT / ".venv" / "bin" / "bea"

LEDGER = """2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD

2026-01-05 * "Café" "Lunch"
  Expenses:Food  12.00 USD
  Assets:Cash
"""

ORIGINAL = b"GOOD\n"
# The formatted ledger is well past this, so the write fails partway through.
BYTE_CAP = 60


def _env(tmp_path: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        # Essential, not tidiness: under the write cap below the interpreter
        # would write truncated `.pyc` files into the shared source tree and
        # every later run would die with "marshal data too short".
        PYTHONDONTWRITEBYTECODE="1",
        TERM="dumb",
        NO_COLOR="1",
    )
    return env


def _cap_writes() -> None:  # pragma: no cover - runs in the forked child
    resource.setrlimit(resource.RLIMIT_FSIZE, (BYTE_CAP, BYTE_CAP))
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)


def _run(books: Path, *args: str, capped: bool = False, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(BEA), *args],
        cwd=books,
        env=_env(books.parent),
        input=stdin,
        stdin=None if stdin is not None else subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        preexec_fn=_cap_writes if capped else None,
    )


@pytest.fixture
def books(tmp_path: Path) -> Path:
    """The ledger's directory, kept apart from the isolated config and cache."""
    directory = tmp_path / "books"
    directory.mkdir()
    (directory / "main.bean").write_text(LEDGER, encoding="utf-8")
    return directory


@pytest.fixture
def export(books: Path) -> Path:
    path = books / "f2.out"
    path.write_bytes(ORIGINAL)
    return path


def _names(books: Path) -> list[str]:
    return sorted(path.name for path in books.iterdir())


@pytest.mark.parametrize(
    ("prefix", "source"),
    [((), "main.bean"), (("--json",), "main.bean"), ((), "-")],
    ids=["text", "json", "stdin"],
)
def test_a_failed_write_preserves_the_previous_export(
    books: Path, export: Path, prefix: tuple[str, ...], source: str
) -> None:
    done = _run(books, *prefix, "format", source, "-o", "f2.out", capped=True, stdin=LEDGER if source == "-" else None)

    assert done.returncode != 0, done.stdout
    assert "File too large" in done.stderr
    assert export.read_bytes() == ORIGINAL, "the last good export must survive a failed write"
    assert _names(books) == ["f2.out", "main.bean"], "no staging file may outlive the failure"


def test_a_failed_write_creates_no_partial_new_file(books: Path) -> None:
    done = _run(books, "format", "main.bean", "-o", "new.out", capped=True)

    assert done.returncode != 0, done.stdout
    assert _names(books) == ["main.bean"]


def test_the_query_export_control_preserves_too(books: Path, export: Path) -> None:
    """The sibling the report compared against."""
    done = _run(
        books,
        "-f",
        "main.bean",
        "query",
        "SELECT account, date, narration, position",
        "-o",
        "f2.out",
        capped=True,
    )

    assert done.returncode != 0, done.stdout
    assert export.read_bytes() == ORIGINAL


@pytest.mark.parametrize("prefix", [(), ("--json",)], ids=["text", "json"])
def test_a_successful_write_still_replaces(books: Path, export: Path, prefix: tuple[str, ...]) -> None:
    """Preserving on failure must not turn into refusing to write on success."""
    done = _run(books, *prefix, "format", "main.bean", "-o", "f2.out")

    assert done.returncode == 0, done.stderr
    assert export.read_text(encoding="utf-8") == _run(books, "format", "main.bean").stdout
    assert "Expenses:Food  12.00 USD" in export.read_text(encoding="utf-8")
    assert _names(books) == ["f2.out", "main.bean"]
