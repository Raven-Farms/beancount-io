"""`price refresh` loads the ledger once, plugins included (w5/432).

It made a full offline load only to record each managed source's previous
revision, then reset the windows and loaded again: every plugin ran twice,
even on a ledger with no managed include. The revisions now come from the
include scan and the cache.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.test_price import _managed_ledger, _run_bea, feed_server  # noqa: F401

COUNTER = """\
from pathlib import Path

__plugins__ = ("count",)


def count(entries, options):
    with (Path(__file__).parent / "runs.txt").open("a") as runs:
        runs.write("run\\n")
    return entries, []
"""
PLUGIN = 'option "insert_pythonpath" "TRUE"\nplugin "counter"\n'


@pytest.mark.parametrize("managed", [False, True], ids=["no-managed-include", "managed-include"])
def test_refresh_runs_each_plugin_once(feed_server: str, tmp_path: Path, managed: bool) -> None:  # noqa: F811
    (tmp_path / "counter.py").write_text(COUNTER)
    ledger = tmp_path / "main.bean"
    body = _managed_ledger(feed_server) if managed else 'option "operating_currency" "USD"\n'
    ledger.write_text(PLUGIN + body)

    result = _run_bea(tmp_path, feed_server, "--file", str(ledger), "price", "refresh")

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "runs.txt").read_text().count("run") == 1
    if managed:
        assert "none → r1" in result.stdout
