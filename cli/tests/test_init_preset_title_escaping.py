"""`init --preset --title` saves the title as supplied (w5/875).

Quotes were deleted and backslashes interpreted as escapes (`C:\\new` became a
newline), and a trailing backslash escaped the closing quote and refused init.
"""

from __future__ import annotations

import pytest
from beancount import loader

from tests.test_init_preset import Path, _bea

TITLES = ['Family "A" ledger', "C:\\new\\test", "Family\\", 'a\\"b', "tab\there", "Café — 家计"]


@pytest.mark.parametrize(
    "title", TITLES, ids=["quotes", "backslashes", "trailing", "backslash-quote", "tab", "unicode"]
)
def test_the_saved_title_equals_the_supplied_one(tmp_path: Path, title: str) -> None:
    books = tmp_path / "books"
    created = _bea(
        tmp_path,
        "--json",
        "init",
        str(books),
        "--preset",
        "personal@1",
        "--currency",
        "USD",
        "--date",
        "2024-02-01",
        "--title",
        title,
    )
    assert created.returncode == 0, created.stderr or created.stdout

    _, errors, options = loader.load_file(str(books / "main.bean"))
    assert not errors
    assert options["title"] == title
