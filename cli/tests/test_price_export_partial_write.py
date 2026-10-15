"""A failed `price export` leaves no partial file behind (w5/409).

Each file was written in place, so a write cut short by a full disk left a
truncated `main.bean` under "Nothing was written", and the retry was then
refused as an overwrite. A file-size limit stands in for a full disk.
"""

from __future__ import annotations

import os
import resource
import signal
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="RLIMIT_FSIZE")


def _limited() -> None:
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024, 1024))


def _bea(books: Path, *args: str, limited: bool = False) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
        preexec_fn=_limited if limited else None,
    )


def test_a_failed_export_leaves_nothing_and_the_retry_succeeds(tmp_path: Path) -> None:
    (tmp_path / "L").mkdir()
    lines = [
        'option "operating_currency" "USD"',
        "2026-01-01 open Assets:Cash USD",
        "2026-01-01 open Expenses:Food USD",
    ]
    for day in range(40):
        lines += [f'2026-02-{day % 28 + 1:02d} * "lunch {day}"', "  Expenses:Food 2.50 USD", "  Assets:Cash"]
    (tmp_path / "L" / "main.bean").write_text("\n".join(lines) + "\n")
    out = tmp_path / "o" / "exp"
    ledger = str(tmp_path / "L" / "main.bean")

    failed = _bea(tmp_path, "-f", ledger, "price", "export", "-o", str(out), limited=True)

    assert failed.returncode == 1, failed.stderr
    assert f"writing {out / 'main.bean'} failed (File too large). Nothing was written." in failed.stderr
    assert not out.exists() or list(out.iterdir()) == []

    retry = _bea(tmp_path, "-f", ledger, "price", "export", "-o", str(out))
    assert retry.returncode == 0, retry.stderr
    assert _bea(tmp_path, "-f", str(out / "main.bean"), "check").returncode == 0
