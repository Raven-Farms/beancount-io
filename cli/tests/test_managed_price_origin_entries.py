"""`MANAGED_PRICE_ORIGINS` entries compare as origins, and a refusal names the real one (w5/480).

Entries were compared as raw strings, so `https://beancount.io/` (the
trailing slash a browser copy carries), `https://Beancount.io` and an
explicit `:443` each refused the origin they name. The refusal also dropped
a non-default port and an IPv6 address's brackets.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from bea_engine.managed_prices import AllowedUrl, RefusedUrl, normalize_origin, parse_managed_price_url

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("entry", "origin"),
    [
        ("https://beancount.io/", "https://beancount.io"),
        ("https://Beancount.io", "https://beancount.io"),
        ("https://beancount.io:443", "https://beancount.io"),
        (" http://127.0.0.1:8080/x ", "http://127.0.0.1:8080"),
        ("http://[::1]:80", "http://[::1]"),
        ("ftp://beancount.io", None),
        ("beancount.io", None),
    ],
)
def test_an_entry_normalizes_to_its_origin(entry: str, origin: str | None) -> None:
    assert normalize_origin(entry) == origin


@pytest.mark.parametrize(
    ("target", "named"),
    [
        ("http://127.0.0.1:8080/prices/BTC-USD", "origin http://127.0.0.1:8080 is not allowlisted"),
        ("http://[::1]:9/prices/BTC-USD", "origin http://[::1]:9 is not allowlisted"),
        ("https://WWW.beancount.io/prices/BTC-USD", "origin https://www.beancount.io is not allowlisted"),
    ],
)
def test_a_refusal_names_the_origin_with_port_and_brackets(target: str, named: str) -> None:
    decision = parse_managed_price_url(target, ("https://beancount.io",))
    assert isinstance(decision, RefusedUrl)
    assert decision.detail.endswith(named)


def test_an_allowed_spelling_still_matches() -> None:
    assert isinstance(parse_managed_price_url("https://beancount.io/prices/BTC-USD"), AllowedUrl)


@pytest.mark.parametrize("entry", ["https://beancount.io/", "https://Beancount.io", "https://beancount.io:443"])
def test_the_environment_spelling_allows_the_include(tmp_path: Path, entry: str) -> None:
    (tmp_path / "main.bean").write_text(
        'include "https://beancount.io/prices/BTC-USD"\n2026-01-01 open Assets:Cash USD\n'
    )
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
        MANAGED_PRICE_ORIGINS=entry,
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--offline", "-f", "main.bean", "check"],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert "not allowlisted" not in result.stdout + result.stderr
    assert "unavailable" in result.stdout + result.stderr
