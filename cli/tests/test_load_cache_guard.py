"""No local command lets Beancount's relocated load cache land on the ledger (w5/067).

Upstream's loader treats its cache path as disposable: a file there that does
not unpickle is removed before the ledger is parsed. With
`BEANCOUNT_LOAD_CACHE_FILENAME` resolving to the root or an include, `bea list`,
`query`, `balance`, `report`, `price status`, `doctor`, `add` and `import`
deleted that file while reading it. w5/065 guarded `bea check` alone.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

MAIN = '2026-01-01 open Assets:Cash USD\n2026-01-01 open Expenses:Uncategorized USD\ninclude "sub/apr.bean"\n'
CHILD = '2026-04-02 note Assets:Cash "cache safety"\n'
EXPORT = "Date,Description,Amount\n2026-05-01,Coffee,-4.50\n"
ENV = "BEANCOUNT_LOAD_CACHE_FILENAME"


def _bea(tmp_path: Path, *args: str, cache: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("BEA_", "BEANCOUNT_"))}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    if cache is not None:
        env[ENV] = cache
    foreign = tmp_path / "foreign"
    foreign.mkdir(exist_ok=True)
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=foreign,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.fixture
def books(tmp_path: Path) -> Path:
    root = tmp_path / "books"
    (root / "sub").mkdir(parents=True)
    (root / "main.bean").write_text(MAIN, encoding="utf-8")
    (root / "sub" / "apr.bean").write_text(CHILD, encoding="utf-8")
    (tmp_path / "bank.csv").write_text(EXPORT, encoding="utf-8")
    return root


def _state(books: Path) -> dict[str, tuple[bool, bytes]]:
    """Every entry under the books, whether it is a link, and the bytes it reaches."""
    return {
        str(path.relative_to(books)): (path.is_symlink(), path.read_bytes() if path.is_file() else b"")
        for path in sorted(books.rglob("*"))
    }


def _command(name: str, books: Path) -> list[str]:
    main = str(books / "main.bean")
    scoped = ["--file", main]
    return {
        "list": [*scoped, "list", "open"],
        "query": [*scoped, "query", "SELECT 1"],
        "balance": [*scoped, "balance"],
        "report": [*scoped, "report", "trial-balance"],
        "price-status": [*scoped, "price", "status"],
        "doctor": ["doctor", "print-options", main],
        "doctor-context": ["doctor", "context", main, f"{main}:1"],
        "add": [*scoped, "add", "note", "-a", "Assets:Cash", "-m", "hi", "--date", "2026-05-01"],
        "import": [*scoped, "import", str(books.parent / "bank.csv"), "--account", "Assets:Cash", "--apply"],
    }[name]


COMMANDS = ["list", "query", "balance", "report", "price-status", "doctor", "doctor-context", "add", "import"]

SPELLINGS = [
    ("pattern", lambda books: "{filename}", "main.bean"),
    ("absolute-root", lambda books: str(books / "main.bean"), "main.bean"),
    ("relative-root", lambda books: "main.bean", "main.bean"),
    ("absolute-include", lambda books: str(books / "sub" / "apr.bean"), "sub/apr.bean"),
    ("relative-include", lambda books: "sub/apr.bean", "sub/apr.bean"),
]


def _refused(result: subprocess.CompletedProcess[str], member: Path) -> None:
    assert result.returncode == 2, result.stderr or result.stdout
    assert ENV in result.stderr
    assert str(member) in result.stderr
    assert "Nothing was changed" in result.stderr
    assert "Cache file is corrupted" not in result.stderr


@pytest.mark.parametrize("command", COMMANDS)
@pytest.mark.parametrize(("build", "member"), [case[1:] for case in SPELLINGS], ids=[case[0] for case in SPELLINGS])
def test_a_cache_variable_naming_a_ledger_file_is_refused_and_deletes_nothing(
    tmp_path: Path, books: Path, command: str, build: object, member: str
) -> None:
    before = _state(books)

    result = _bea(tmp_path, *_command(command, books), cache=build(books))  # type: ignore[operator]

    assert _state(books) == before
    _refused(result, books / member)


@pytest.mark.skipif(sys.platform == "win32", reason="needs symlinks and hard links")
@pytest.mark.parametrize("command", ["list", "doctor", "add"])
@pytest.mark.parametrize("kind", ["symlink", "hard-link"])
@pytest.mark.parametrize("target", ["main.bean", "sub/apr.bean"])
def test_a_cache_variable_linked_to_a_ledger_file_is_refused(
    tmp_path: Path, books: Path, command: str, kind: str, target: str
) -> None:
    alias = books / "cache.pkl"
    if kind == "symlink":
        alias.symlink_to(books / target)
    else:
        os.link(books / target, alias)
    before = _state(books)

    result = _bea(tmp_path, *_command(command, books), cache=str(alias))

    assert _state(books) == before
    _refused(result, books / target)


@pytest.mark.parametrize("command", COMMANDS)
def test_a_cache_path_outside_the_ledger_keeps_working(tmp_path: Path, books: Path, command: str) -> None:
    ledger = {name: state for name, state in _state(books).items()}

    result = _bea(tmp_path, *_command(command, books), cache="other.cache")

    assert result.returncode == 0, result.stderr or result.stdout
    after = _state(books)
    if command in ("add", "import"):
        assert after["main.bean"] != ledger.pop("main.bean")
    assert {name: after[name] for name in ledger} == ledger
