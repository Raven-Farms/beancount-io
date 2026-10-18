"""A proxy's HTML error page is reported by its status, not printed (w5/482).

A non-JSON body passed through as the server's sentence, so a CDN's 501
page reached the user as 18 lines of markup; the cloud commands said
`Server error (HTTP 501).`
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cli.errors import server_message
from tests.test_ask_auth_failures import _ask

PAGE = """<!DOCTYPE HTML>
<html lang="en">
  <head><title>Error response</title></head>
  <body>
    <h1>Error response</h1>
    <p>Error code: 501</p>
  </body>
</html>
"""


@pytest.mark.parametrize(
    "body",
    [
        PAGE,
        "<html><body>Bad Gateway</body></html>",
        "\ufeff<html><body><h1>502 Bad Gateway</h1></body></html>",
        "line one\nline two",
        "word " * 60,
    ],
    ids=["html-page", "one-line-markup", "marked-markup", "several-lines", "long-text"],
)
def test_a_page_is_no_sentence(body: str) -> None:
    assert server_message(body) is None


def test_a_short_plain_sentence_still_passes() -> None:
    assert server_message("Upstream model is overloaded; retry shortly.") == (
        "Upstream model is overloaded; retry shortly."
    )


def test_a_multi_line_message_inside_json_is_kept() -> None:
    assert server_message({"message": "Ledger locked.\nRetry in a minute."}) == "Ledger locked.\nRetry in a minute."


def test_ask_reports_the_status(tmp_bean_file: Path, logged_in: None) -> None:
    result = _ask(tmp_bean_file, 501, PAGE)

    assert result.exit_code == 1, result.output
    assert "Server error (HTTP 501)." in result.output
    assert "<" not in result.output


def test_ask_keeps_a_short_plain_sentence(tmp_bean_file: Path, logged_in: None) -> None:
    result = _ask(tmp_bean_file, 503, "Upstream model is overloaded; retry shortly.")

    assert result.exit_code == 1, result.output
    assert "Upstream model is overloaded; retry shortly." in result.output


def test_ask_reports_a_marked_page_by_its_status(tmp_bean_file: Path, logged_in: None) -> None:
    """`strip()` keeps a byte-order mark, so a marked page passed as the message (w5/649)."""
    result = _ask(tmp_bean_file, 502, "\ufeff<html><body><h1>502 Bad Gateway</h1></body></html>")

    assert result.exit_code == 1, result.output
    assert "Server error (HTTP 502)." in result.output
    assert "<" not in result.output and "\ufeff" not in result.output


def test_a_marked_json_envelope_still_reads() -> None:
    assert server_message('\ufeff{"message": "Ledger locked."}') == "Ledger locked."
