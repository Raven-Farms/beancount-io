"""`import --apply` queues behind a write to an include in another directory (w5/869).

The apply decided under a lock on the root and target only, so a `format -i`
to an include elsewhere committed mid-import and the import refused with
exit 4, "The ledger changed during the operation". The deciding lock now
covers the whole graph the import reads, as `add`'s does (w5/718).
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from tests.test_cross_directory_writes_queue import _books, _env, _misalign

ROUNDS = 3


def test_import_apply_and_format_in_another_directory_both_land(tmp_path: Path) -> None:
    books = _books(tmp_path)
    env = _env(tmp_path)
    main = str(books / "main.bean")
    leaf = str(books / "2024" / "jan.bean")
    for round_number in range(ROUNDS):
        _misalign(books, f"r{round_number}")
        export = tmp_path / f"imp{round_number}.csv"
        export.write_text(f"Date,Amount,Description\n2024-02-0{round_number + 1},-3.00,Coffee{round_number}\n")
        imported = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "cli.main",
                "-f",
                main,
                "import",
                str(export),
                "--csv",
                "date=Date,amount=Amount,narration=Description",
                "--account",
                "Assets:Cash",
                "--default-account",
                "Expenses:Food",
                "--apply",
            ],
            env=env,
            cwd=tmp_path,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        # The import loads ~20k transactions under its locks; the format
        # starts mid-window so the two overlap.
        time.sleep(0.5)
        formatted = subprocess.run(
            [sys.executable, "-m", "cli.main", "format", "-i", leaf],
            env=env,
            cwd=tmp_path,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=120,
        )
        try:
            out, err = imported.communicate(timeout=240)
        except subprocess.TimeoutExpired:
            imported.kill()
            raise
        assert formatted.returncode == 0, formatted.stdout + formatted.stderr
        assert imported.returncode == 0, out + err

    text = (books / "main.bean").read_text(encoding="utf-8")
    for round_number in range(ROUNDS):
        assert text.count(f'"Coffee{round_number}"') == 1, text[-800:]
    assert "  Assets:Cash\n" in (books / "2024" / "jan.bean").read_text(encoding="utf-8")
