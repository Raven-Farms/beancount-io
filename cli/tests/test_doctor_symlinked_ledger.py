"""`bea doctor` reads a symlinked ledger at the path named, as `check` and `list` do (w5/568).

Upstream's doctor resolves its ledger argument's symlinks, so its entries
carried the real path: a location under a linked folder matched nothing, and
a linked root file read the includes beside its target instead of beside the
link.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TXNS = '2024-01-05 * "a" ^grp\n  Expenses:Food  10 USD\n  Assets:Cash\n'


def _doctor(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(cwd / ".config"),
        XDG_CACHE_HOME=str(cwd / ".cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "doctor", *args],
        env=env,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.fixture
def linked_folder(tmp_path: Path) -> Path:
    (tmp_path / "real" / "books" / "txns").mkdir(parents=True)
    (tmp_path / "real" / "books" / "main.bean").write_text(
        'include "txns/jan.bean"\n2024-01-01 open Assets:Cash USD\n2024-01-01 open Expenses:Food USD\n'
    )
    (tmp_path / "real" / "books" / "txns" / "jan.bean").write_text(TXNS)
    (tmp_path / "link").symlink_to("real")
    return tmp_path


@pytest.mark.parametrize(
    ("op", "location", "expected"),
    [("context", "txns/jan.bean:1", "Location: {base}/books/txns/jan.bean:1"), ("region", "txns/jan.bean:1:3", "Food")],
)
def test_locations_under_a_linked_folder_match_as_through_the_real_one(
    linked_folder: Path, op: str, location: str, expected: str
) -> None:
    for base in ("real", "link"):
        result = _doctor(linked_folder, op, f"{base}/books/main.bean", location)

        assert result.returncode == 0, f"{base}: {result.stdout + result.stderr}"
        assert expected.format(base=linked_folder / base) in result.stdout, result.stdout


def test_a_linked_root_file_reads_the_includes_beside_the_link(tmp_path: Path) -> None:
    (tmp_path / "shared").mkdir()
    (tmp_path / "books" / "txns").mkdir(parents=True)
    (tmp_path / "shared" / "main.bean").write_text('include "txns/jan.bean"\n2024-01-01 open Assets:Cash USD\n')
    (tmp_path / "books" / "main.bean").symlink_to("../shared/main.bean")
    (tmp_path / "books" / "txns" / "jan.bean").write_text(TXNS)

    missing = _doctor(tmp_path, "missing-open", "books/main.bean")
    linked = _doctor(tmp_path, "linked", "books/main.bean", "^grp")
    options = _doctor(tmp_path, "print-options", "books/main.bean")

    assert missing.stdout.strip() == "2024-01-05 open Expenses:Food", missing.stdout + missing.stderr
    assert linked.returncode == 0 and f"{tmp_path / 'books' / 'txns' / 'jan.bean'}:1:" in linked.stdout, linked.stderr
    assert str(tmp_path / "books" / "txns" / "jan.bean") in options.stdout, options.stdout
