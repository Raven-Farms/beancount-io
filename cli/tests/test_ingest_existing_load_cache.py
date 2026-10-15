"""`ingest extract -e LEDGER` keeps the ledger's load cache private (w5/456).

Beangulp loads the `-e` ledger through Beancount, whose default cache is a
pickle of every entry written beside the ledger with the process umask — a
world-readable copy of a `0600` ledger, left after the command exits. Every
other load bea starts caches under its own `0700` directory (w5/175).
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

# A load that takes more than Beancount's one-second threshold is cached; the
# plugin's pause gets a tiny ledger there without generating thousands of rows.
SLOW_PLUGIN = textwrap.dedent(
    """
    import time
    __plugins__ = ["slow"]
    def slow(entries, options):
        time.sleep(1.2)
        return entries, []
    """
)
LEDGER = 'option "insert_pythonpath" "TRUE"\nplugin "slow_plugin"\n2026-01-01 open Assets:Cash USD\n'
SCRIPT = textwrap.dedent(
    """
    from beangulp import Ingest
    if __name__ == "__main__":
        Ingest([])()
    """
)


@pytest.mark.usefixtures("use_optional_engine")
def test_the_existing_ledger_is_cached_privately(tmp_path: Path) -> None:
    books = tmp_path / "books"
    books.mkdir()
    (books / "slow_plugin.py").write_text(SLOW_PLUGIN)
    ledger = books / "main.bean"
    ledger.write_text(LEDGER)
    ledger.chmod(0o600)
    script = tmp_path / "ingest.py"
    script.write_text(SCRIPT)
    downloads = tmp_path / "downloads"
    downloads.mkdir()

    result = runner.invoke(app, ["ingest", "extract", "--config", str(script), "-e", str(ledger), str(downloads)])

    assert result.exit_code == 0, result.output
    assert not (books / ".main.bean.picklecache").exists()
    cached = list((Path(os.environ["XDG_CACHE_HOME"]) / "bea" / "load-cache").glob("*.main.bean.picklecache"))
    assert len(cached) == 1


def test_bean_price_is_told_which_ledger_it_loads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # beanprice is optional and absent in the suite's engine, so the handoff is
    # what is checked: the ledger it loads reaches `run_native`, which places
    # its load cache as for every native.
    from cli.engine import launch

    ledger = tmp_path / "main.bean"
    ledger.write_text("")
    seen: dict[str, object] = {}

    def run_native(name: str, args: list[str], **kwargs: object) -> int:
        seen.update(name=name, **kwargs)
        return 0

    monkeypatch.setattr(launch, "require_feature", lambda _feature: None)
    monkeypatch.setattr(launch, "run_native", run_native)
    result = runner.invoke(app, ["price", str(ledger)])
    assert result.exit_code == 0, result.output
    assert seen["name"] == "bean-price"
    assert seen["ledger"] == str(ledger)
