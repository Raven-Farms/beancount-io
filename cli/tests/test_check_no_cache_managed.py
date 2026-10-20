"""`check` on a managed ledger honours `--no-cache` and the disable variable (w5/776).

A stale `.managed` load cache (same size and mtime, so the fingerprint
holds — upstream's own cache behaves the same) could not be bypassed:
`BEANCOUNT_DISABLE_LOAD_CACHE` was ignored and `check --no-cache` was
refused as an unforwardable bean-check option. Both now force a fresh load.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from tests.test_price import _cli_env
from tests.test_price import feed_server as feed_server

TXN = '2024-02-01 * "Lunch"\n  Expenses:Food  5 USD\n  Assets:Cash\n'
COUNT = 40000


def _run(
    tmp_path: Path, feed_server: str, *args: str, extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    env = _cli_env(tmp_path, feed_server)
    env.update(extra_env or {})
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_no_cache_and_the_variable_bypass_a_stale_managed_cache(feed_server: str, tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(
        f"""option "operating_currency" "USD"
include "{feed_server}/prices/BTC-USD"
2024-01-01 open Assets:Cash USD
2024-01-01 open Expenses:Food USD
2024-01-01 commodity BTC
include "txns.bean"
"""
    )
    txns = tmp_path / "txns.bean"
    txns.write_text(TXN * COUNT)

    warm = _run(tmp_path, feed_server, "--file", str(tmp_path / "main.bean"), "check")
    assert warm.returncode == 0, warm.stderr
    cached = _run(tmp_path, feed_server, "--file", str(tmp_path / "main.bean"), "check")
    assert cached.returncode == 0, cached.stderr
    assert list((tmp_path / "cache").rglob("*.managed")), "fixture did not warm the managed cache"

    before = txns.stat()
    txns.write_text(TXN * (COUNT - 1) + TXN.replace("Expenses:Food", "Expenses:Fodo"))
    os.utime(txns, ns=(before.st_atime_ns, before.st_mtime_ns))

    stale = _run(tmp_path, feed_server, "--file", str(tmp_path / "main.bean"), "check")
    assert stale.returncode == 0, stale.stderr

    flag = _run(tmp_path, feed_server, "--file", str(tmp_path / "main.bean"), "check", "--no-cache")
    assert flag.returncode == 1, flag.stderr
    assert "Expenses:Fodo" in flag.stdout + flag.stderr

    forced = _run(
        tmp_path,
        feed_server,
        "--file",
        str(tmp_path / "main.bean"),
        "check",
        extra_env={"BEANCOUNT_DISABLE_LOAD_CACHE": "1"},
    )
    assert forced.returncode == 1, forced.stderr
    assert "Expenses:Fodo" in forced.stdout + forced.stderr
