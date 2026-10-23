"""Writes to includes in another directory queue instead of failing with exit 4 (w5/718).

`add` locked only the root and the target, so a `format -i` (or another
root's write) to an include in a different directory committed past those
locks and tripped the snapshot check with "The ledger changed during the
operation". Writers now lock every file their snapshot reads; `format -i`
needs no change, since its exclusive target lock is what the other writer
queues on.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TRANSACTIONS = 20000
ROUNDS = 5


def _env(tmp_path: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return env


def _books(tmp_path: Path) -> Path:
    books = tmp_path / "books"
    (books / "2024").mkdir(parents=True)
    lines = [
        'option "operating_currency" "USD"',
        "2024-01-01 open Assets:Cash USD",
        "2024-01-01 open Expenses:Food USD",
        'include "2024/jan.bean"',
    ]
    for number in range(TRANSACTIONS):
        lines.append(f'2024-01-{(number % 28) + 1:02d} txn "P{number:05d}"')
        lines.append("  Expenses:Food  1.00 USD")
        lines.append("  Assets:Cash")
    (books / "main.bean").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return books


def _misalign(books: Path, tag: str) -> None:
    (books / "2024" / "jan.bean").write_text(
        f'2024-01-05 txn "Misaligned{tag}"\n  Expenses:Food   2.00 USD\n Assets:Cash\n', encoding="utf-8"
    )


def test_add_and_format_in_another_directory_both_land(tmp_path: Path) -> None:
    books = _books(tmp_path)
    env = _env(tmp_path)
    main = str(books / "main.bean")
    leaf = str(books / "2024" / "jan.bean")
    for round_number in range(ROUNDS):
        # Between rounds only: each round's format must really change the
        # leaf, or there is no race to queue through.
        _misalign(books, f"r{round_number}")
        tag = f"Coffee{round_number}"
        add = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "cli.main",
                "-f",
                main,
                "add",
                "transaction",
                tag,
                "--date",
                "2024-02-01",
                "-p",
                "Expenses:Food 3.00 USD",
                "-p",
                "Assets:Cash",
            ],
            env=env,
            cwd=tmp_path,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        # The add validates ~20k transactions under its locks; the format
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
            out, err = add.communicate(timeout=240)
        except subprocess.TimeoutExpired:
            add.kill()
            raise
        assert formatted.returncode == 0, formatted.stdout + formatted.stderr
        assert add.returncode == 0, out + err

    text = (books / "main.bean").read_text(encoding="utf-8")
    for round_number in range(ROUNDS):
        assert f'"Coffee{round_number}"' in text, text[-500:]
    assert "  Assets:Cash\n" in (books / "2024" / "jan.bean").read_text(encoding="utf-8")


def test_locked_graph_falls_back_to_narrow_locks_without_descriptors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A graph too wide to hold open still writes, serialized as before (w5/718)."""
    from bea_engine.ledger import write as ledger_write

    books = tmp_path / "books"
    (books / "2024").mkdir(parents=True)
    (books / "main.bean").write_text(
        'option "operating_currency" "USD"\n2024-01-01 open Assets:Cash USD\n'
        "2024-01-01 open Expenses:Food USD\n"
        'include "2024/jan.bean"\n',
        encoding="utf-8",
    )
    (books / "2024" / "jan.bean").write_text('2024-01-05 txn "M"\n  Expenses:Food  2.00 USD\n  Assets:Cash\n')
    seen: list[list[Path]] = []
    real_lock_files = ledger_write.lock_files

    def recording_lock_files(files, **kwargs):
        seen.append(list(files))
        return real_lock_files(files, **kwargs)

    monkeypatch.setattr(ledger_write, "descriptors_allow", lambda locks: False)
    monkeypatch.setattr(ledger_write, "lock_files", recording_lock_files)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    root = books / "main.bean"
    with ledger_write.locked_graph(root, root) as snapshot:
        assert set(snapshot.contents) == {root, books / "2024" / "jan.bean"}

    assert len(seen) == 1
    assert {path.name for path in seen[0]} == {"main.bean"}
