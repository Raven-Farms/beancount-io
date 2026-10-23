"""Bank-export framing imports: preamble skip, sep= line, repeated headers, footers (w5/758).

A preamble, an Excel `sep=;` first line, a header repeated per page, and a
footer line each refused with advice that could not work (`--csv` naming
columns the file "lacks", `--date-format` for a footer), and a duplicated
column name was offered a `--csv` line that was then refused.

`--csv skip=N` now starts the header after N leading records (remembered and
replayed like the other reading keys); exact header repeats are skipped with
a note; a row no known date format reads is refused as not a data row; and
identical column names get rename advice instead of an example.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

LEDGER = """option "operating_currency" "USD"
2020-01-01 open Assets:Checking USD
2020-01-01 open Expenses:Uncategorized
"""

SPEC = "date=Date,amount=Amount,narration=Description"

PREAMBLE = """Account Number: ****1234
Statement Period: Jan 2024

Date,Description,Amount
2024-01-05,Salary,1995.50
"""

SEP = """sep=;
Date;Description;Amount
2024-01-05;Salary;1995.50
"""

REPEAT = """Date,Description,Amount
2024-01-05,Salary,1995.50
Date,Description,Amount
2024-01-06,Bonus,100.00
"""

FOOTER = """Date,Description,Amount
2024-01-05,Salary,1995.50
End of statement,,
"""

DUP = """Date,Description,Amount,Description
2024-01-05,Salary,1995.50,X
"""

ROOT = Path(__file__).resolve().parents[1]


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
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content)
    return path


def test_preamble_hint_names_line_and_skip(tmp_path: Path) -> None:
    ledger = _write(tmp_path, "main.bean", LEDGER)
    csv = _write(tmp_path, "pa.csv", PREAMBLE)
    proc = _bea(tmp_path, "--file", str(ledger), "import", str(csv), "--account", "Assets:Checking")
    assert proc.returncode == 2
    assert "Line 4 of pa.csv looks like the header row. Pass --csv skip=3 to start there." in proc.stderr


def test_preamble_auto_hint_names_line_and_skip(tmp_path: Path) -> None:
    ledger = _write(tmp_path, "main.bean", LEDGER)
    csv = _write(tmp_path, "pa.csv", PREAMBLE)
    proc = _bea(tmp_path, "--file", str(ledger), "import", str(csv), "--account", "Assets:Checking", "--csv", "auto")
    assert proc.returncode == 2
    assert (
        "Cannot read a column mapping from line 1 of pa.csv: line 4 looks like the header row. "
        "Pass --csv skip=3 to start there." in proc.stderr
    )


def test_preamble_explicit_mapping_hint_names_line(tmp_path: Path) -> None:
    ledger = _write(tmp_path, "main.bean", LEDGER)
    csv = _write(tmp_path, "pa.csv", PREAMBLE)
    proc = _bea(tmp_path, "--file", str(ledger), "import", str(csv), "--account", "Assets:Checking", "--csv", SPEC)
    assert proc.returncode == 2
    assert "but pa.csv has 'Date' on line 4. Pass --csv skip=3 to start the header there." in proc.stderr


def test_preamble_skip_imports_and_replays(tmp_path: Path) -> None:
    ledger = _write(tmp_path, "main.bean", LEDGER)
    csv = _write(tmp_path, "pa.csv", PREAMBLE)
    proc = _bea(
        tmp_path,
        "--file",
        str(ledger),
        "import",
        str(csv),
        "--account",
        "Assets:Checking",
        "--csv",
        f"{SPEC},skip=3",
        "--apply",
    )
    assert proc.returncode == 0, proc.stderr
    assert "Wrote 1 entry" in proc.stderr + proc.stdout
    replay = _bea(tmp_path, "--file", str(ledger), "import", str(csv), "--account", "Assets:Checking")
    assert replay.returncode == 0, replay.stderr
    assert "skip=3" in replay.stderr + replay.stdout
    assert "Nothing new to import." in replay.stderr + replay.stdout


def test_sep_line_hint_and_skip(tmp_path: Path) -> None:
    ledger = _write(tmp_path, "main.bean", LEDGER)
    csv = _write(tmp_path, "sep.csv", SEP)
    hint = _bea(tmp_path, "--file", str(ledger), "import", str(csv), "--account", "Assets:Checking")
    assert hint.returncode == 2
    assert "Line 2 of sep.csv looks like the header row. Pass --csv skip=1 to start there." in hint.stderr
    proc = _bea(
        tmp_path,
        "--file",
        str(ledger),
        "import",
        str(csv),
        "--account",
        "Assets:Checking",
        "--csv",
        f"{SPEC},skip=1",
        "--apply",
    )
    assert proc.returncode == 0, proc.stderr
    assert "Wrote 1 entry" in proc.stderr + proc.stdout


def test_repeated_header_skipped_with_note(tmp_path: Path) -> None:
    ledger = _write(tmp_path, "main.bean", LEDGER)
    csv = _write(tmp_path, "repeat.csv", REPEAT)
    proc = _bea(tmp_path, "--file", str(ledger), "import", str(csv), "--account", "Assets:Checking", "--apply")
    assert proc.returncode == 0, proc.stderr
    out = proc.stderr + proc.stdout
    assert "Skipped 1 repeated header line(s) (3); they are page breaks, not data." in out
    assert "Wrote 2 entries" in out


def test_recall_does_not_replay_skip_across_header_lines(tmp_path: Path) -> None:
    ledger = _write(tmp_path, "main.bean", LEDGER)
    sep = _write(tmp_path, "sep.csv", SEP)
    first = _bea(
        tmp_path,
        "--file",
        str(ledger),
        "import",
        str(sep),
        "--account",
        "Assets:Checking",
        "--csv",
        f"{SPEC},skip=1",
        "--apply",
    )
    assert first.returncode == 0, first.stderr
    # Same header text at line 1 must not replay sep.csv's skip=1.
    lined = _write(
        tmp_path,
        "lined.csv",
        "Date,Description,Amount\n2024-01-05,Salary,1995.50\n2024-01-06,Bonus,100.00\n",
    )
    proc = _bea(tmp_path, "--file", str(ledger), "import", str(lined), "--account", "Assets:Checking")
    assert proc.returncode == 0, proc.stderr
    assert "skip=1" not in proc.stderr + proc.stdout


def test_footer_refused_as_not_a_data_row(tmp_path: Path) -> None:
    ledger = _write(tmp_path, "main.bean", LEDGER)
    csv = _write(tmp_path, "foot.csv", FOOTER)
    proc = _bea(tmp_path, "--file", str(ledger), "import", str(csv), "--account", "Assets:Checking")
    assert proc.returncode == 2
    assert (
        "Row 2 (line 3): 'End of statement' in column 'Date' is not a data row. "
        "Remove the line and import again." in proc.stderr
    )
    assert "pass --date-format" not in proc.stderr


def test_duplicate_column_advises_rename_without_example(tmp_path: Path) -> None:
    ledger = _write(tmp_path, "main.bean", LEDGER)
    csv = _write(tmp_path, "dup.csv", DUP)
    proc = _bea(tmp_path, "--file", str(ledger), "import", str(csv), "--account", "Assets:Checking")
    assert proc.returncode == 2
    assert "rename the duplicates so each mapped column is unique" in proc.stderr
    assert "For example:" not in proc.stderr


def test_bad_skip_refused_before_reading(tmp_path: Path) -> None:
    ledger = _write(tmp_path, "main.bean", LEDGER)
    csv = _write(tmp_path, "pa.csv", PREAMBLE)
    bad = _bea(
        tmp_path,
        "--file",
        str(ledger),
        "import",
        str(csv),
        "--account",
        "Assets:Checking",
        "--csv",
        f"{SPEC},skip=x",
    )
    assert bad.returncode == 2
    assert "Bad --csv skip 'x': use a whole number of leading rows." in bad.stderr
    past_end = _bea(
        tmp_path,
        "--file",
        str(ledger),
        "import",
        str(csv),
        "--account",
        "Assets:Checking",
        "--csv",
        f"{SPEC},skip=9",
    )
    assert past_end.returncode == 2
    assert "skip=9 skips every record of pa.csv" in past_end.stderr
