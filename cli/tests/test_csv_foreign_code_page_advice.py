"""A CSV in another code page is told to re-save as UTF-8, not to read as cp1252 (w5/529).

Almost any 8-bit file decodes as cp1252, so a cp1250 or cp1251 export got
"pass --csv encoding=cp1252", and following it wrote `Wp³ata £ódŸ` with exit 0.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "EUR"
2026-01-01 open Assets:Checking EUR
2026-01-01 open Expenses:Uncategorized EUR
"""


def _import(tmp_path: Path, text: str, codec: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "s.csv").write_bytes(f"Date,Description,Amount\n2026-03-01,{text},-4.50\n".encode(codec))
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
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), "import", "s.csv"]
        + ["--account", "Assets:Checking"],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize(
    ("text", "codec", "shown"),
    [("Wpłata Łódź", "cp1250", "Wp³ata"), ("Пятёрочка", "cp1251", "Ïÿò¸ðî÷êà"), ("Tip 5€", "iso-8859-15", "5¤")],
    ids=["cp1250", "cp1251", "latin-9"],
)
def test_another_code_page_is_told_to_resave_as_utf8(tmp_path: Path, text: str, codec: str, shown: str) -> None:
    result = _import(tmp_path, text, codec)

    assert result.returncode == 2, result.stdout + result.stderr
    flat = " ".join(result.stderr.split())
    assert f"Read as cp1252 it shows {shown!r}" in flat
    assert "Re-save the export as UTF-8 and import it again" in flat
    assert "it decodes as cp1252 — pass --csv encoding=cp1252." not in flat


def test_a_western_cp1252_export_keeps_the_cp1252_hint(tmp_path: Path) -> None:
    result = _import(tmp_path, "Café Crème Œuvre Ærø Größe ¿Qué? £5", "cp1252")

    assert result.returncode == 2, result.stdout + result.stderr
    assert "it decodes as cp1252 — pass --csv encoding=cp1252." in result.stderr
