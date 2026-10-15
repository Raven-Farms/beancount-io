"""A failed load-cache write does not leak Beancount's raw log line (w5/411).

Upstream logs a cache it could not write through the root logger, so a read
on a full disk printed `WARNING:root:Could not write to picklecache file …`
beside a correct answer. A plugin's own log lines still show.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_a_failed_cache_write_is_quiet_and_plugin_logs_still_show(tmp_path: Path) -> None:
    plugins = tmp_path / "plugins"
    plugins.mkdir()
    (plugins / "slow_plugin.py").write_text(
        textwrap.dedent(
            """
            import logging
            import time
            __plugins__ = ["slow"]
            def slow(entries, options):
                logging.warning("slow plugin says hello")
                time.sleep(1.2)
                return entries, []
            """
        )
    )
    (tmp_path / "main.bean").write_text(
        'plugin "slow_plugin"\noption "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n'
    )
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=os.pathsep.join([str(ROOT / "src"), str(plugins)]),
        TERM="dumb",
        NO_COLOR="1",
        # A directory that does not exist: the cache write fails like a full disk.
        BEANCOUNT_LOAD_CACHE_FILENAME=str(tmp_path / "missing" / "ledger.picklecache"),
    )

    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), "balance"],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )

    assert result.returncode == 0, result.stderr
    assert "picklecache" not in result.stderr
    assert "slow plugin says hello" in result.stderr
