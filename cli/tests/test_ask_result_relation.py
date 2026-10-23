"""Ask names the relation a query reads from its code, not its literals or comments (w5/892).

`WHERE narration ~ 'from entries'` was taken for `FROM entries`, and a comment
between `FROM` and `#entries` hid the real one, so the result was labelled
with the wrong table and a posting count lost (or wrongly gained) its warning.
"""

from __future__ import annotations

import pytest

from cli.ask.results import format_result, table_named

COUNT = {"columns": [{"name": "count(*)", "type": "int"}], "rows": [[4]]}


@pytest.mark.parametrize(
    ("query", "table"),
    [
        ("SELECT count(*) WHERE narration ~ 'from entries'", "postings"),
        ("SELECT count(*) /* from entries */ WHERE narration ~ '(from) entries'", "postings"),
        ("SELECT count(*) -- from entries\nWHERE account = 'Assets:Cash'", "postings"),
        ("SELECT count(*) FROM /* choose entry source */ #entries WHERE type = 'transaction'", "entries"),
        ("SELECT count(*) FROM #entries WHERE type = 'transaction'", "entries"),
        ('SELECT count(*) FROM "entries"', "entries"),
        ("SELECT 'it''s from entries' FROM #prices", "prices"),
    ],
    ids=["literal", "comment-and-regex", "line-comment", "commented-from", "plain-entries", "quoted", "escaped-quote"],
)
def test_the_relation_comes_from_code(query: str, table: str) -> None:
    assert table_named(query) == table


def test_a_posting_count_keeps_its_warning_and_an_entry_count_does_not() -> None:
    postings = format_result("SELECT count(*) WHERE narration ~ 'from entries'", COUNT)
    entries = format_result("SELECT count(*) FROM /* source */ #entries WHERE type = 'transaction'", COUNT)

    assert postings.startswith("1 row(s) from the postings table (one row per posting")
    assert "count(*) counts postings, not transactions" in postings
    assert entries.startswith("1 row(s) from the entries table.")
    assert "counts postings" not in entries
