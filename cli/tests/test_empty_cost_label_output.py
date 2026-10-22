"""An explicitly empty lot label survives the table and query CSV (w5/872).

`if cost.get("label")` treated `""` like `None`, so the table and CSV spelled an
empty label as an unlabeled lot while JSON and `--details` kept it.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """\
2024-01-01 open Assets:Stock HOOL
2024-01-01 open Assets:Cash USD
2024-02-01 * "unlabeled"
  Assets:Stock 1 HOOL {100 USD}
  Assets:Cash -100 USD
2024-02-01 * "empty"
  Assets:Stock 1 HOOL {100 USD, ""}
  Assets:Cash -100 USD
2024-02-01 * "named"
  Assets:Stock 1 HOOL {100 USD, "lot-a"}
  Assets:Cash -100 USD
"""


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
        COLUMNS="200",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
        stdin=subprocess.DEVNULL,
    )


def test_empty_label_kept_in_table_and_csv(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")
    before = ledger.read_bytes()

    table = _bea(tmp_path, "--file", str(ledger), "list", "transaction")
    assert table.returncode == 0, table.stderr
    assert "1 HOOL {100 USD, 2024-02-01}" in table.stdout
    assert '1 HOOL {100 USD, 2024-02-01, ""}' in table.stdout
    assert '1 HOOL {100 USD, 2024-02-01, "lot-a"}' in table.stdout

    position = _bea(
        tmp_path, "--file", str(ledger), "query", "SELECT position WHERE account = 'Assets:Stock'", "--format", "csv"
    )
    assert position.returncode == 0, position.stderr
    assert '"1 HOOL {100 USD, 2024-02-01}"' in position.stdout
    assert '"1 HOOL {100 USD, 2024-02-01, """"}"' in position.stdout
    assert '"1 HOOL {100 USD, 2024-02-01, ""lot-a""}"' in position.stdout

    bare = _bea(
        tmp_path,
        "--file",
        str(ledger),
        "query",
        "SELECT position.cost WHERE account = 'Assets:Stock'",
        "--format",
        "csv",
    )
    assert bare.returncode == 0, bare.stderr
    assert '""""' in bare.stdout
    assert ledger.read_bytes() == before
