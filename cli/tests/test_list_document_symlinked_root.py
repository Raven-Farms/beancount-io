"""`list document` under a symlinked root ledger lists the path as written (w5/170)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = '2024-01-01 open Assets:Cash\n2024-01-02 document Assets:Cash "receipts/r.pdf"\n'


def _bea(cwd: Path, home: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(home / "config"),
        XDG_CACHE_HOME=str(home / "cache"),
        XDG_DATA_HOME=str(home / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _books(tmp_path: Path) -> Path:
    """`books/main.bean` links to a ledger in `store/`; `books/plain.bean` is the same text as a file."""
    books = tmp_path / "books"
    (books / "receipts").mkdir(parents=True)
    (books / "receipts" / "r.pdf").write_bytes(b"x")
    (tmp_path / "store").mkdir()
    (tmp_path / "store" / "ledger.bean").write_text(LEDGER, encoding="utf-8")
    (books / "main.bean").symlink_to(Path("..") / "store" / "ledger.bean")
    (books / "plain.bean").write_text(LEDGER, encoding="utf-8")
    return books


@pytest.mark.parametrize("name", ["main.bean", "plain.bean"], ids=["symlinked-root", "regular-root"])
def test_document_beside_the_root_lists_as_the_ledger_spells_it(tmp_path: Path, name: str) -> None:
    books = _books(tmp_path)

    listed = _bea(books, tmp_path, "--json", "--file", str(books / name), "list", "document")
    assert listed.returncode == 0, listed.stderr
    assert [row["filename"] for row in json.loads(listed.stdout)["data"]] == ["receipts/r.pdf"]

    text = _bea(books, tmp_path, "--file", str(books / name), "list", "document")
    assert text.returncode == 0, text.stderr
    assert "receipts/r.pdf" in text.stdout
    assert str(tmp_path) not in text.stdout


def test_listed_value_under_a_symlinked_root_is_accepted_by_add_document(tmp_path: Path) -> None:
    books = _books(tmp_path)
    ledger = str(books / "main.bean")

    listed = _bea(books, tmp_path, "--json", "--file", ledger, "list", "document")
    assert listed.returncode == 0, listed.stderr
    filename = json.loads(listed.stdout)["data"][0]["filename"]

    added = _bea(
        books,
        tmp_path,
        *("--json", "--file", ledger, "add", "document", "--date", "2024-01-03"),
        *("--account", "Assets:Cash", "--path", filename),
    )
    assert added.returncode == 0, added.stderr
    assert json.loads(added.stdout)["data"]["directive"]["filename"] == "receipts/r.pdf"

    relisted = _bea(books, tmp_path, "--json", "--file", ledger, "list", "document")
    assert relisted.returncode == 0, relisted.stderr
    assert [row["filename"] for row in json.loads(relisted.stdout)["data"]] == ["receipts/r.pdf"] * 2
