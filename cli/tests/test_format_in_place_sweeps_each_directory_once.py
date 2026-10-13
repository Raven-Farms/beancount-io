"""`format -i` sweeps each directory once, not once per file (w5/125).

The in-place loop cleared abandoned staging files before every file it handled,
and a sweep lists the whole directory. A flat directory of thousands of ledger
files — one per day, say — therefore formatted in quadratic time: 4,000 files
took 17 s where `format --check` took 1.6 s, with nothing to rewrite.

The note's reproducer is a timing run. These tests pin what made it possible
instead — the number of directory listings — and that the sweep still happens
in every directory the run writes to.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bea_engine.ledger import formatting
from bea_engine.ledger import write as ledger_write
from cli.main import app

runner = CliRunner()

HEADER = "2000-01-01 open Assets:Bank USD\n2000-01-01 open Expenses:Food USD\n"
ALIGNED = '2020-01-01 * "t{index}"\n  Expenses:Food  1 USD\n  Assets:Bank\n\n'
# Three-space posting indents, so the file needs rewriting.
MISALIGNED = '2020-01-01 * "t{index}"\n   Expenses:Food 1 USD\n   Assets:Bank\n\n'


def _books(root: Path, files: int) -> list[Path]:
    """A main file including a flat `inc/` of `files` one-entry ledgers."""
    included = root / "inc"
    included.mkdir()
    main = root / "main.bean"
    main.write_text(HEADER + 'include "inc/*.bean"\n', encoding="utf-8")
    targets = [main]
    for index in range(files):
        target = included / f"f{index:04d}.bean"
        target.write_text(ALIGNED.format(index=index), encoding="utf-8")
        targets.append(target)
    return targets


def _aged(path: Path) -> Path:
    path.touch()
    old = time.time() - ledger_write._ABANDONED_CANDIDATE_SECONDS * 2
    os.utime(path, (old, old))
    return path


def _format_in_place(targets: list[Path]) -> dict[str, object]:
    return formatting.format_files(targets, in_place=True, prefix_width=None, num_width=None, currency_column=None)


def test_a_flat_directory_is_listed_once_however_many_files_it_holds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    targets = _books(tmp_path, files=40)
    swept: list[Path] = []
    real_sweep = ledger_write.sweep_abandoned_candidates

    def counting_sweep(directory: Path) -> None:
        swept.append(directory)
        real_sweep(directory)

    monkeypatch.setattr(ledger_write, "sweep_abandoned_candidates", counting_sweep)

    assert _format_in_place(targets) == {"changed": []}

    root = tmp_path.resolve()
    assert sorted(swept) == [root, root / "inc"]


def test_the_sweep_runs_before_any_file_is_rewritten(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Hoisting the sweep must not move it behind the writes it tidies up for."""
    targets = _books(tmp_path, files=3)
    rewritten = targets[1]
    rewritten.write_text(MISALIGNED.format(index=0), encoding="utf-8")
    seen_before_sweep: list[str] = []
    real_sweep = ledger_write.sweep_abandoned_candidates

    def recording_sweep(directory: Path) -> None:
        seen_before_sweep.append(rewritten.read_text(encoding="utf-8"))
        real_sweep(directory)

    monkeypatch.setattr(ledger_write, "sweep_abandoned_candidates", recording_sweep)

    assert _format_in_place(targets) == {"changed": [str(rewritten.resolve())]}

    assert seen_before_sweep == [MISALIGNED.format(index=0)] * 2
    assert rewritten.read_text(encoding="utf-8") == ALIGNED.format(index=0)


def test_format_in_place_still_clears_abandoned_candidates_in_every_directory(tmp_path: Path) -> None:
    targets = _books(tmp_path, files=3)
    rewritten = targets[1]
    rewritten.write_text(MISALIGNED.format(index=0), encoding="utf-8")
    stale_beside_main = _aged(tmp_path / ".bea-left-by-a-kill.tmp")
    stale_beside_include = _aged(tmp_path / "inc" / ".bea-left-by-a-kill.tmp")
    fresh = tmp_path / "inc" / ".bea-in-flight.tmp"
    fresh.touch()

    result = runner.invoke(app, ["format", "-i", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "1/4 file(s) formatted." in result.output
    assert rewritten.read_text(encoding="utf-8") == ALIGNED.format(index=0)
    assert not stale_beside_main.exists()
    assert not stale_beside_include.exists()
    assert fresh.exists()


def test_check_leaves_abandoned_candidates_alone(tmp_path: Path) -> None:
    """The control: `--check` writes nothing, so it has nothing to tidy up after."""
    _books(tmp_path, files=3)
    stale = _aged(tmp_path / "inc" / ".bea-left-by-a-kill.tmp")

    result = runner.invoke(app, ["format", "--check", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "All 4 file(s) are formatted." in result.output
    assert stale.exists()
