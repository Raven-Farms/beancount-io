"""A plugin entry that borrows a real line on the same date is not "on disk" (w5/401).

`entry_generated` judged location, date and leading token only, so a new
transaction a plugin stamped with its source's own line and date passed:
`--on-disk` kept a row `grep` cannot find, and `--details` labelled it with
the source's line.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = textwrap.dedent(
    """
    from decimal import Decimal
    from beancount.core import data
    __plugins__ = ["run"]
    def run(entries, options_map, config=None):
        out = []
        for e in entries:
            out.append(e)
            if isinstance(e, data.Transaction) and "inv" in e.tags:
                meta = data.new_metadata(e.meta["filename"], e.meta["lineno"])
                fee = [
                    data.Posting("Expenses:Fees", data.Amount(Decimal("1"), "USD"), None, None, None, None),
                    data.Posting("Assets:Cash", data.Amount(Decimal("-1"), "USD"), None, None, None, None),
                ]
                out.append(data.Transaction(
                    meta, e.date, "*", "Broker", "fee (generated)", frozenset({"gen"}), frozenset(), fee
                ))
        return out, []
    """
)
LEDGER = """plugin "myplug"
option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Fees USD
2026-01-01 open Equity:Opening USD
2026-01-02 * "seed"
  Assets:Cash 1000 USD
  Equity:Opening
2026-01-05 * "Broker" "buy" #inv
  Expenses:Fees 10 USD
  Assets:Cash
"""


def _list(books: Path, *args: str) -> list[dict[str, object]]:
    (books / "plugins").mkdir(exist_ok=True)
    (books / "plugins" / "myplug.py").write_text(PLUGIN)
    (books / "main.bean").write_text(LEDGER)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=os.pathsep.join([str(ROOT / "src"), str(books / "plugins")]),
        TERM="dumb",
        NO_COLOR="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "-f", str(books / "main.bean"), "list", "transaction", *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 0, result.stderr
    items: list[dict[str, object]] = json.loads(result.stdout)["data"]
    return items


def test_on_disk_answers_what_the_file_holds(tmp_path: Path) -> None:
    assert sorted(str(item["narration"]) for item in _list(tmp_path, "--on-disk")) == ["buy", "seed"]
    assert _list(tmp_path, "--tag", "gen", "--on-disk") == []


def test_the_borrowed_line_is_labelled_generated(tmp_path: Path) -> None:
    flags = {str(item["narration"]): item.get("generated", False) for item in _list(tmp_path)}
    assert flags == {"fee (generated)": True, "buy": False, "seed": False}
