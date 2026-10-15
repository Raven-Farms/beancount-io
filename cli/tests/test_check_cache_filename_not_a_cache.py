"""`bea check --cache-filename` never deletes a file that is no load cache (w5/417).

bean-check removes a cache file it cannot unpickle, so a mistyped path to a
statement CSV deleted it with exit 0 and a raw `ERROR:root:` line; under
`-C` stock bean-check also logs `WARNING:root:Cache disabled …`.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n'


def _check(books: Path, *args: str, plugins: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "BEANCOUNT_LOAD_CACHE_FILENAME"}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=os.pathsep.join([str(ROOT / "src"), *([str(plugins)] if plugins else [])]),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(books / "main.bean"), "check", *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def test_a_statement_named_as_the_cache_is_refused_and_kept(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    statement = tmp_path / "stmt.csv"
    statement.write_text("Date,Amount\n2026-01-05,-5\n")

    result = _check(tmp_path, "--cache-filename", str(statement))

    assert result.returncode == 2, result.stderr
    assert f"--cache-filename {statement} names {statement}, which is not a Beancount load cache" in result.stderr
    assert "or leave it out. Nothing was changed." in result.stderr
    assert "root:" not in result.stderr
    assert statement.read_text() == "Date,Amount\n2026-01-05,-5\n"


def test_no_cache_drops_the_ignored_path_in_bea_words(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    result = _check(tmp_path, "-C", "--cache-filename", str(tmp_path / "x.cache"))
    assert result.returncode == 0, result.stderr
    assert "--no-cache turns the load cache off, so --cache-filename is ignored." in result.stderr
    assert "WARNING:root" not in result.stderr


def test_a_real_cache_at_the_path_still_works(tmp_path: Path) -> None:
    """A load over Beancount's one-second threshold writes the cache the next check reads."""
    plugins = tmp_path / "plugins"
    plugins.mkdir()
    (plugins / "slow_plugin.py").write_text(
        textwrap.dedent(
            """
            import time
            __plugins__ = ["slow"]
            def slow(entries, options):
                time.sleep(1.2)
                return entries, []
            """
        )
    )
    (tmp_path / "main.bean").write_text('plugin "slow_plugin"\n' + LEDGER)
    cache = tmp_path / "ledger.picklecache"

    first = _check(tmp_path, "--cache-filename", str(cache), plugins=plugins)
    assert first.returncode == 0, first.stderr
    assert cache.is_file()

    second = _check(tmp_path, "--cache-filename", str(cache), plugins=plugins)
    assert second.returncode == 0, second.stderr
    assert "root:" not in second.stderr
