"""A stdout that refuses a write (full disk, size limit) gets bea's sentence and exit 1 (w5/407).

Only a broken pipe was handled. Any other failed write was reported as a raw
`[Errno 27] File too large`, and the bytes still buffered failed again at the
shutdown flush: `Exception ignored on flushing sys.stdout` and the
undocumented exit 120. A file-size limit stands in for a full disk; stderr
stays a pipe so the report itself can be read.
"""

from __future__ import annotations

import json
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
    resource.setrlimit(resource.RLIMIT_FSIZE, (512, 512))


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    lines = [
        'option "operating_currency" "USD"',
        "2026-01-01 open Assets:Cash USD",
        "2026-01-01 open Expenses:Food USD",
    ]
    for day in range(60):
        lines += [
            f'2026-02-{day % 28 + 1:02d} * "lunch {day} with a long narration"',
            "  Expenses:Food 2 USD",
            "  Assets:Cash",
        ]
    (books / "main.bean").write_text("\n".join(lines) + "\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    with (books / "out").open("w") as out:
        return subprocess.run(
            [sys.executable, "-m", "cli.main", "-f", str(books / "main.bean"), *args],
            env=env,
            cwd=books,
            stdout=out,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
            stdin=subprocess.DEVNULL,
            preexec_fn=_limited,
        )


@pytest.mark.parametrize(
    "args",
    [["--help"], ["list", "transaction"], ["query", "SELECT date, narration, position"], ["report", "balance-sheet"]],
    ids=["help", "list", "query", "report"],
)
def test_a_refused_stdout_write_exits_1_with_the_sentence(tmp_path: Path, args: list[str]) -> None:
    result = _bea(tmp_path, *args)
    assert result.returncode == 1, result.stderr
    assert "Error: Could not write output: File too large.\n" in result.stderr
    assert "Exception ignored" not in result.stderr
    assert "Errno" not in result.stderr


def test_json_reports_it_in_the_envelope(tmp_path: Path) -> None:
    result = _bea(tmp_path, "--json", "list", "transaction")
    assert result.returncode == 1, result.stderr
    assert json.loads(result.stderr)["error"]["message"] == "Could not write output: File too large."
