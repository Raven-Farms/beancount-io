"""`list --type` and the CSV header hint fold Turkish İ/ı, as `--search` does (w5/533).

Both used a plain `casefold()`, under which `İ` becomes `i` plus a combining
dot: `-t ikamet` found nothing for `event "İkamet"`, and `işlem tarihi` got
no hint toward the header `İşlem Tarihi`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = '2026-01-01 open Expenses:İstanbul\n2026-01-09 event "İkamet" "x"\n2026-01-09 custom "İzin" "x"\n'


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize(("kind", "term", "found"), [("event", "ikamet", "İkamet"), ("custom", "izin", "İzin")])
def test_type_folds_turkish_i(tmp_path: Path, kind: str, term: str, found: str) -> None:
    result = _bea(tmp_path, "--json", "list", kind, "-t", term)

    assert result.returncode == 0, result.stderr
    assert [row["type"] for row in json.loads(result.stdout)["data"]] == [found]


def test_the_header_hint_folds_turkish_i(tmp_path: Path) -> None:
    (tmp_path / "tr.csv").write_text("İşlem Tarihi,Açıklama,Tutar\n2026-03-01,Kahve,-4.50\n")

    result = _bea(
        tmp_path, "import", "tr.csv", "--csv", "date=işlem tarihi,narration=Açıklama,amount=Tutar",
        "--account", "Expenses:İstanbul",
    )  # fmt: skip

    assert result.returncode == 2
    assert "Did you mean 'İşlem Tarihi'?" in result.stderr
