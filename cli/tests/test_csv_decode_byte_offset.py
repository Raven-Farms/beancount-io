"""A CSV decode error past the first 8 KiB names the absolute byte offset (w5/717).

Text-mode iteration decodes chunk by chunk, so past the first chunk the
exception's `start` was the offset within its 8192-byte chunk: a bad byte at
file offset 10038 was reported as byte 1846.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Uncategorized USD
"""


def _late_csv(rows: int) -> bytes:
    body = "".join(f"2026-03-01,Row{i:04d},-1.00\n" for i in range(rows))
    return ("Date,Description,Amount\n" + body + "2026-03-02,Caf\xe9,-4.50\n").encode("latin-1")


def _import(csv_name: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
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
        [sys.executable, "-m", "cli.main", "-f", str(tmp_path / "main.bean"), "import", csv_name]
        + ["--account", "Assets:Checking"],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_a_late_decode_error_names_the_file_offset(tmp_path: Path) -> None:
    raw = _late_csv(400)
    assert raw.index(0xE9) == 10038
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "late.csv").write_bytes(raw)

    result = _import("late.csv", tmp_path)

    assert result.returncode == 2, result.stdout + result.stderr
    assert "invalid continuation byte at byte 10038" in result.stderr


def test_an_early_decode_error_is_unchanged(tmp_path: Path) -> None:
    raw = _late_csv(0)
    assert raw.index(0xE9) == 38
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "early.csv").write_bytes(raw)

    result = _import("early.csv", tmp_path)

    assert result.returncode == 2, result.stdout + result.stderr
    assert "invalid continuation byte at byte 38" in result.stderr


@pytest.mark.parametrize("module", ["cli.csv_mapper", "bea_engine.csv_mapper"])
def test_the_offset_is_recomputed_from_the_raw_bytes(tmp_path: Path, module: str) -> None:
    import importlib

    mapper = importlib.import_module(module)
    raw = _late_csv(400)
    source = tmp_path / "late.csv"
    source.write_bytes(raw)
    chunked = UnicodeDecodeError("utf-8", raw[8192:8193], 1846, 1847, "invalid continuation byte")

    assert mapper._absolute_offset(source, chunked, "utf-8") == 10038


@pytest.mark.parametrize("module", ["cli.csv_mapper", "bea_engine.csv_mapper"])
def test_a_vanished_file_keeps_the_chunk_offset(tmp_path: Path, module: str) -> None:
    import importlib

    mapper = importlib.import_module(module)
    chunked = UnicodeDecodeError("utf-8", b"\xe9", 1846, 1847, "invalid continuation byte")

    assert mapper._absolute_offset(tmp_path / "gone.csv", chunked, "utf-8") == 1846
