"""`doctor roundtrip` refuses duplicate entries and uncreatable scratch files in one line (w5/770).

Two bugs in one command, both real-command failures:

1. Two *identical* entries — valid for `check` — died in upstream
   `compare_entries` with a 30-line `ValueError: CompareError(... Duplicate
   entry...)` traceback and a swallowed verdict. bea names the lines in one
   line instead.
2. A ledger whose name is long enough that `…roundtrip1.bean` exceeds the
   filesystem limit died with an `OSError` double traceback: upstream crashed
   in its own cleanup (`stat` of a file it never created). Every scratch
   pre-create failure, not only the permission ones (w5/572), is now refused
   in one line naming the scratch file.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_roundtrip(ledger: Path, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "doctor", "roundtrip", str(ledger)],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_identical_transactions_name_their_lines_in_one_line(tmp_path: Path) -> None:
    books = tmp_path / "books"
    books.mkdir()
    ledger = books / "main.bean"
    ledger.write_text(
        "2026-01-01 open Assets:Cash USD\n"
        "2026-01-01 open Expenses:Food USD\n"
        "\n"
        '2026-01-05 * "Coffee"\n'
        "  Expenses:Food  3.00 USD\n"
        "  Assets:Cash\n"
        "\n"
        '2026-01-05 * "Coffee"\n'
        "  Expenses:Food  3.00 USD\n"
        "  Assets:Cash\n"
    )

    result = _run_roundtrip(ledger, tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stderr.splitlines() == [
        f"Error: doctor roundtrip cannot compare {ledger}: lines 4 and 8 hold identical transactions"
        ' ("Coffee" on 2026-01-05). Roundtrip compares entry sets, so it cannot tell them apart;'
        " add a link or tag to one to make the file roundtrip-clean."
    ]


def test_identical_notes_name_their_lines_in_one_line(tmp_path: Path) -> None:
    books = tmp_path / "books"
    books.mkdir()
    ledger = books / "notes.bean"
    ledger.write_text(
        '2026-01-01 open Assets:Cash USD\n\n2026-01-05 note Assets:Cash "hi"\n\n2026-01-05 note Assets:Cash "hi"\n'
    )

    result = _run_roundtrip(ledger, tmp_path)

    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stderr.splitlines() == [
        f"Error: doctor roundtrip cannot compare {ledger}: lines 3 and 5 hold identical notes"
        ' ("hi" on 2026-01-05). Roundtrip compares entry sets, so it cannot tell them apart;'
        " change one so they differ."
    ]


def test_an_uncreatable_scratch_file_names_the_problem_in_one_line(tmp_path: Path) -> None:
    books = tmp_path / "books"
    books.mkdir()
    # The first scratch copy appends 14 characters (`roundtrip1.bean` minus
    # one); a 245-character stem dies with ENAMETOOLONG at the pre-create.
    ledger = books / ("N" * 241 + ".bean")
    ledger.write_text("2026-01-01 open Assets:Cash USD\n")

    result = _run_roundtrip(ledger, tmp_path)

    scratch = books / ("N" * 241 + ".roundtrip1.bean")
    assert result.returncode == 2, result.stdout + result.stderr
    assert result.stderr.splitlines() == [
        f"Error: doctor roundtrip cannot create its scratch file {scratch}: File name too long. Nothing was written."
    ]
    assert sorted(path.name for path in books.iterdir()) == [ledger.name]
