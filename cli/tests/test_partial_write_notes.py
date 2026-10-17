"""A `--partial` write that wrote rows prints what their write noted, in text too (w5/541).

w5/461 keeps a refused write's terminal output to what forced the refusal.
A partial write that wrote rows was not refused, but the same rule dropped
the NFC/NFD account note for the rows it wrote; `--json` kept it as
`error.ledger_warnings`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NFD = unicodedata.normalize("NFD", "Café")
NFC = unicodedata.normalize("NFC", "Café")
LEDGER = f"2026-01-01 open Expenses:Food USD\n2026-01-01 open Assets:{NFD} USD\n"
NOTE = f"The new directive spells Assets:{NFC} as"
LUNCH = {
    "date": "2026-02-01",
    "narration": "lunch",
    "postings": [{"account": "Expenses:Food", "amount": "5 USD"}, {"account": f"Assets:{NFC}"}],
}
NOPE = {
    **LUNCH,
    "narration": "nope",
    "postings": [{"account": "Expenses:Nope", "amount": "5 USD"}, {"account": f"Assets:{NFC}"}],
}


def _add(tmp_path: Path, rows: list[dict[str, object]], *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER, encoding="utf-8")
    (tmp_path / "rows.json").write_text(json.dumps(rows), encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", "main.bean", "add", "transactions", "--from", "rows.json", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def test_the_written_rows_note_prints_beside_the_partial_refusal(tmp_path: Path) -> None:
    result = _add(tmp_path, [LUNCH, NOPE], "--partial")

    assert result.returncode == 1, result.stderr
    lines = result.stderr.splitlines()
    notes = [number for number, line in enumerate(lines) if line.startswith(NOTE)]
    assert len(notes) == 1, result.stderr
    # Before the outcome line, as a clean write prints its notes before "Added".
    assert notes[0] < lines.index("Error: Added 1 of 2 transactions; 1 row was rejected."), result.stderr
    assert '"lunch"' in (tmp_path / "main.bean").read_text(encoding="utf-8")


def test_a_refused_batch_still_names_only_the_refusal(tmp_path: Path) -> None:
    """w5/461's rule stands where nothing was written."""
    result = _add(tmp_path, [LUNCH, NOPE])

    assert result.returncode == 1, result.stderr
    assert NOTE not in result.stderr
    assert result.stderr.startswith("Error: "), result.stderr
    assert (tmp_path / "main.bean").read_text(encoding="utf-8") == LEDGER
