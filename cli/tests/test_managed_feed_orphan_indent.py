"""A feed body whose indented line Beancount would read as orphaned is refused (w5/478).

The validator skipped blank and comment lines without ending the point, so
metadata after a blank line still attached. Beancount reads it as a stray
indented line: the refresh exited 0, replaced the last good revision, and
every later command failed with `unexpected INDENT`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from beancount.parser import parser

from bea_engine.managed_prices import InvalidFeed, ValidFeed, validate_managed_price_text
from tests.test_price import _FeedHandler, _run_bea
from tests.test_price import feed_server as feed_server

HEAD = "; alias: K1\n; commodity: XA\n; quote: USD\n"
GOOD = HEAD + '2026-10-15 price XA 10 USD\n  observed-at: "2026-10-16T12:00:00Z"\n'
BAD = {
    "blank-line": HEAD + '2026-10-16 price XA 11 USD\n\n  observed-at: "2026-10-16T12:00:00Z"\n',
    "whitespace-line": HEAD + '2026-10-16 price XA 11 USD\n   \n  observed-at: "2026-10-16T12:00:00Z"\n',
    "column-0-comment": HEAD + '2026-10-16 price XA 11 USD\n; note\n  observed-at: "2026-10-16T12:00:00Z"\n',
    "indented-comment-first": HEAD + "  ; note\n2026-10-16 price XA 11 USD\n",
}
FINE = {
    "indented-comment-in-metadata": HEAD
    + '2026-10-16 price XA 11 USD\n    ; note\n  observed-at: "2026-10-16T12:00:00Z"\n',
    "blank-between-points": HEAD + "2026-10-16 price XA 11 USD\n\n2026-10-17 price XA 12 USD\n",
}


@pytest.mark.parametrize("name", list(BAD))
def test_a_body_beancount_cannot_parse_is_refused(name: str) -> None:
    assert parser.parse_string(BAD[name])[1], "the fixture must be one Beancount refuses"
    assert isinstance(validate_managed_price_text(BAD[name]), InvalidFeed)


@pytest.mark.parametrize("name", list(FINE))
def test_a_body_beancount_parses_is_accepted(name: str) -> None:
    assert not parser.parse_string(FINE[name])[1]
    assert isinstance(validate_managed_price_text(FINE[name]), ValidFeed)


def _serve(body: str, etag: str) -> None:
    _FeedHandler.routes["/prices/K1"] = {
        "body": body.encode(),
        "headers": {"Content-Type": "text/plain; charset=utf-8", "ETag": etag},
        "etag": etag,
        "etag_match": True,
    }


def test_a_refused_refresh_keeps_the_good_revision(feed_server: str, tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(f'include "{feed_server}/prices/K1"\n2026-01-01 open Assets:Cash USD\n')
    _serve(GOOD, '"good"')
    assert _run_bea(tmp_path, feed_server, "--file", str(ledger), "check").returncode == 0

    _serve(BAD["blank-line"], '"bad"')
    refreshed = _run_bea(tmp_path, feed_server, "--file", str(ledger), "price", "refresh")

    assert refreshed.returncode == 1, refreshed.stdout + refreshed.stderr
    checked = _run_bea(tmp_path, feed_server, "--file", str(ledger), "check")
    assert checked.returncode == 0, checked.stdout + checked.stderr
    prices = _run_bea(tmp_path, feed_server, "--file", str(ledger), "list", "price")
    assert "10 USD" in prices.stdout and "11 USD" not in prices.stdout
