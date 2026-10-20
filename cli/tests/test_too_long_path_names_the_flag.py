"""A name longer than the filesystem allows is a usage error naming the flag (w5/817).

Since Python 3.12 `Path.exists()` raises ENAMETOOLONG rather than answering
False, so a 256-byte name given to `-f`, `-o` or `--into` exited 1 with a raw
`[Errno 63] File name too long` (`OSError:` first for `--into` and `price
export`). Each is now exit 2 naming the flag, and nothing is written.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LONG = "Q" * 256
LEDGER = 'option "operating_currency" "USD"\n2020-01-01 open Assets:Bank USD\ninclude "inc/*.bean"\n'

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX name limits")


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "inc").mkdir()
    (tmp_path / "inc" / "notes.bean").write_text("")
    return tmp_path


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", *args],
        cwd=books,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


COMMANDS: dict[str, tuple[Callable[[Path], list[str]], str]] = {
    "query -o": (lambda b: ["-f", str(b / "main.bean"), "query", "SELECT date", "-o", str(b / LONG)], "--output"),
    "format -o": (lambda b: ["-f", str(b / "main.bean"), "format", "-o", str(b / LONG)], "--output"),
    "example -o": (lambda b: ["example", "-o", str(b / LONG)], "--output"),
    "treeify -o": (lambda b: ["-f", str(b / "main.bean"), "treeify", "-o", str(b / LONG)], "--output"),
    "ingest extract -o": (
        lambda b: ["-f", str(b / "main.bean"), "ingest", "extract", "-o", str(b / LONG), str(b / "main.bean")],
        "--output",
    ),
    "price export -o": (lambda b: ["-f", str(b / "main.bean"), "price", "export", "-o", str(b / LONG)], "-o"),
    "-f": (lambda b: ["-f", str(b / "inc" / LONG), "check"], "Ledger path (from --file)"),
    "--into": (
        lambda b: (
            ["-f", str(b / "main.bean"), "add", "note", "-a", "Assets:Bank", "-m", "x"]
            + ["--date", "2020-03-01", "--into", f"inc/{LONG}.bean"]
        ),
        "--into",
    ),
}


@pytest.mark.parametrize("command", sorted(COMMANDS))
def test_a_too_long_name_is_a_usage_error_naming_the_flag(books: Path, command: str) -> None:
    build, named = COMMANDS[command]
    before = sorted(path.name for path in books.rglob("*") if "cache" not in path.parts and "config" not in path.parts)

    result = _bea(books, *build(books))

    assert result.returncode == 2, result.stderr
    message = " ".join(result.stderr.split())
    assert f"{named} " in message
    assert "has a name too long for the filesystem; choose a shorter one." in message
    for raw in ("Errno", "OSError", "Traceback"):
        assert raw not in message
    after = sorted(path.name for path in books.rglob("*") if "cache" not in path.parts and "config" not in path.parts)
    assert after == before


def test_a_name_at_the_limit_still_writes(books: Path) -> None:
    result = _bea(books, "-f", str(books / "main.bean"), "query", "SELECT date", "-o", str(books / ("Q" * 255)))

    assert result.returncode == 0, result.stderr
    assert (books / ("Q" * 255)).is_file()
