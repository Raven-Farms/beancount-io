"""The import preview is UTF-8 on stdout under an 8-bit locale (w5/532).

The summary, row table and diff printed in the locale's codec: `é` as one
byte and `東京` as `\\u6771\\u4eac`, in the text `--apply` is approved on.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Café USD
"""


def test_the_preview_is_utf8(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "bank.csv").write_text("Date,Description,Amount\n2026-03-01,Café Zürich,-4.50\n2026-03-02,東京,-1.00\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        PYTHONIOENCODING="latin-1",
        TERM="dumb",
        NO_COLOR="1",
    )

    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), "import", "bank.csv"]
        + ["--account", "Assets:Checking", "--default-account", "Expenses:Café"],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=120,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    text = result.stdout.decode("utf-8")  # raises if any of it is not UTF-8
    assert "csv → Assets:Checking: 2 ready" in text
    assert "東京" in text and "Café Zürich" in text
    assert "\\u6771" not in text
