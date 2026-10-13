"""`--on-disk` reads each include file once, however many there are (w5/206).

`entry_generated()` asks for an entry's source lines once per entry, and the
lines were cached with `lru_cache(maxsize=64)`. Entries arrive in date order,
so a ledger split into more than 64 include files whose entries interleave
evicted and re-read a whole file for nearly every entry: 40,000 transactions
took twice as long in 100 files as in 50.
"""

from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from beancount import loader
from beancount.core import data

from bea_engine.ledger import reader

ROOT = Path(__file__).resolve().parents[1]
ROUNDS = 6


def _write_ledger(work: Path, files: int) -> Path:
    """One include file per payee; every date has one transaction in each file."""
    (work / "inc").mkdir()
    main = work / "main.bean"
    main.write_text(
        "2000-01-01 open Assets:Bank USD\n2000-01-01 open Expenses:Food USD\n"
        + "".join(f'include "inc/f{index:03d}.bean"\n' for index in range(files)),
        encoding="utf-8",
    )
    for index in range(files):
        (work / "inc" / f"f{index:03d}.bean").write_text(
            "".join(
                f'{datetime.date(2000, 1, 1) + datetime.timedelta(days=day)} * "P{index}" "t{day}"\n'
                "  Expenses:Food  1.25 USD\n  Assets:Bank\n\n"
                for day in range(ROUNDS)
            ),
            encoding="utf-8",
        )
    return main


def _bea(work: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(work / "config"),
        XDG_CACHE_HOME=str(work / "cache"),
        XDG_DATA_HOME=str(work / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=work,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=120,
    )


@pytest.mark.parametrize("files", [70, 8])
def test_each_source_file_is_read_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, files: int) -> None:
    main = _write_ledger(tmp_path, files)
    entries, errors, _ = loader.load_file(str(main))
    assert errors == []
    transactions = [entry for entry in entries if isinstance(entry, data.Transaction)]
    assert len(transactions) == files * ROUNDS
    # The interleaving that defeated the bounded cache: consecutive entries
    # come from different files, and each file comes round again later.
    assert len({entry.meta["filename"] for entry in transactions[:files]}) == files

    reads: list[str] = []
    real_read_bytes = Path.read_bytes

    def counting_read_bytes(self: Path) -> bytes:
        reads.append(str(self))
        return real_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", counting_read_bytes)
    resolves: list[str] = []
    real_resolve = Path.resolve

    def counting_resolve(self: Path, strict: bool = False) -> Path:
        resolves.append(str(self))
        return real_resolve(self, strict=strict)

    monkeypatch.setattr(Path, "resolve", counting_resolve)

    assert not any(reader.entry_generated(entry, "transaction") for entry in transactions)

    sources = sorted(str(tmp_path / "inc" / f"f{index:03d}.bean") for index in range(files))
    assert sorted(reads) == sources
    # The managed-price-cache test is per file too, not per entry.
    assert sorted(path for path in resolves if path in sources) == sources


def test_on_disk_lists_the_same_rows_across_seventy_files(tmp_path: Path) -> None:
    main = _write_ledger(tmp_path, 70)
    plain = _bea(tmp_path, "-f", str(main), "--json", "list", "transaction", "-l", "1000")
    on_disk = _bea(tmp_path, "-f", str(main), "--json", "list", "transaction", "-l", "1000", "--on-disk")
    assert plain.returncode == 0, plain.stderr
    assert on_disk.returncode == 0, on_disk.stderr
    rows = json.loads(on_disk.stdout)["data"]
    assert rows == json.loads(plain.stdout)["data"]
    assert len(rows) == 70 * ROUNDS
