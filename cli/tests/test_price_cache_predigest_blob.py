"""A cached feed revision without a digest is re-validated before it is trusted (w5/423).

bea 0.3.0 and 0.3.1 wrote sidecars without `sha256` and could cache a
truncated download. `_read_blob` checked the digest only when one was there,
so such a blob was trusted, its ETag earned 304s, and every read failed until
the cache was deleted by hand.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from bea_engine.managed_price_cache import feed_dir
from tests.test_price import FEED, _FeedHandler, _resolve, feed_server  # noqa: F401


def _predigest(feed_server: str, root: Path, text: str) -> Path:  # noqa: F811
    """Make the cached r1 look as 0.3.x left it: no digest, the given text."""
    directory = feed_dir(f"{feed_server}/prices/BTC-USD", root)
    sidecar = directory / "r1.json"
    raw = json.loads(sidecar.read_text())
    raw.pop("sha256")
    sidecar.write_text(json.dumps(raw))
    (directory / "r1.beancount").write_text(text)
    return directory / "r1.beancount"


@pytest.mark.parametrize(
    "cut",
    [FEED.index("113500") + 3, FEED.index("2026-09-11")],
    ids=["mid-line", "line-boundary"],
)
def test_a_truncated_predigest_blob_is_refetched_in_full(
    feed_server: str,  # noqa: F811
    tmp_path: Path,
    cut: int,
) -> None:
    now = time.time()
    root = tmp_path / "cache"
    assert _resolve(feed_server, root, now=now).blob is not None
    blob = _predigest(feed_server, root, FEED[:cut])
    _FeedHandler.seen_headers.clear()

    healed = _resolve(feed_server, root, now=now + 301)

    assert "if-none-match" not in _FeedHandler.seen_headers["/prices/BTC-USD"]
    assert healed.blob is not None and healed.blob.text == FEED
    assert blob.read_text() == FEED
    assert "sha256" in json.loads((blob.parent / "r1.json").read_text())


def test_an_intact_predigest_blob_is_still_served(feed_server: str, tmp_path: Path) -> None:  # noqa: F811
    now = time.time()
    root = tmp_path / "cache"
    assert _resolve(feed_server, root, now=now).blob is not None
    _predigest(feed_server, root, FEED)

    served = _resolve(feed_server, root, now=now + 1, offline=True)

    assert served.blob is not None and served.blob.text == FEED
    assert served.head.revision == "r1"
