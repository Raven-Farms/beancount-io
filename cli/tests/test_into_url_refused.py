"""`--into` a URL is refused, never written as a local path (w5/449).

As a `Path`, `--into "https://beancount.io/prices/BTC-USD"` became the local
`https:/beancount.io/prices/BTC-USD`: bea advised creating that directory,
then wrote the entry into a file the ledger never loads, with exit 0.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
include "https://beancount.io/prices/BTC-USD"
2026-01-01 open Assets:Cash USD
"""
CSV = "Date,Description,Amount\n2026-03-01,Coffee,-3.00\n"


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--offline", "-f", str(books / "mp.bean"), *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


IMPORT = ["import", "bank.csv", "--csv", "date=Date,narration=Description,amount=Amount,currency=USD"]
IMPORT += ["--account", "Assets:Cash", "--apply"]
NOTE = ["add", "note", "--date", "2026-01-05", "-a", "Assets:Cash", "-m", "x", "--into"]


@pytest.mark.skipif(os.name != "posix", reason="':' in a directory name")
@pytest.mark.parametrize("url", ["https://beancount.io/prices/BTC-USD", "HTTPS://beancount.io/prices/BTC-USD"])
def test_a_managed_feed_is_read_only_even_once_its_path_exists(tmp_path: Path, url: str) -> None:
    (tmp_path / "mp.bean").write_text(LEDGER)
    for _ in range(2):
        result = _bea(tmp_path, *NOTE, url)
        assert result.returncode == 2, result.stderr
        assert f"--into '{url}' names a URL" in result.stderr
        assert "managed price feed is read-only" in result.stderr
        assert "Create the directory" not in result.stderr
        (tmp_path / url.split("//")[0] / "beancount.io" / "prices").mkdir(parents=True, exist_ok=True)
    assert not (tmp_path / url.split("//")[0] / "beancount.io" / "prices" / "BTC-USD").exists()
    assert (tmp_path / "mp.bean").read_text() == LEDGER


@pytest.mark.parametrize(
    "args",
    [
        ["add", "transactions", "--from", "rows.json", "--into"],
        [*IMPORT, "--into"],
        ["ask", "What is my cash?", "--print", "--into"],
    ],
    ids=["bulk-add", "import", "ask"],
)
def test_every_writer_refuses_a_file_url(tmp_path: Path, args: list[str]) -> None:
    (tmp_path / "mp.bean").write_text(LEDGER)
    (tmp_path / "rows.json").write_text("[]")
    (tmp_path / "bank.csv").write_text(CSV)
    url = f"file://{tmp_path}/x.bean"
    result = _bea(tmp_path, *args, url)
    assert result.returncode == 2, result.stderr
    assert f"--into '{url}' names a URL" in result.stderr
    assert "managed price feed" not in result.stderr
    assert not (tmp_path / "x.bean").exists()
