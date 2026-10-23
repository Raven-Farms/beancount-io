"""`--json` `target.file` names a symlinked root as the command read it (w5/581).

`file_target` resolved the path, so for `A/main.bean -> ../B/real.bean` it
named `B/real.bean`, which on its own loads the includes beside the target and
fails: an agent re-running on `target.file` got a different, broken ledger.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _bea(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(cwd.parent / "config"),
        XDG_CACHE_HOME=str(cwd.parent / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.fixture
def linked(tmp_path: Path) -> Path:
    (tmp_path / "A").mkdir()
    (tmp_path / "B").mkdir()
    (tmp_path / "B" / "real.bean").write_text(
        'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n2026-01-01 open Expenses:Food USD\n'
        'include "inc.bean"\n'
    )
    (tmp_path / "A" / "inc.bean").write_text('2026-01-05 * "lunch"\n  Expenses:Food  5 USD\n  Assets:Cash\n')
    (tmp_path / "A" / "main.bean").symlink_to("../B/real.bean")
    return tmp_path / "A"


def test_a_read_names_the_link_and_rerunning_on_it_agrees(linked: Path) -> None:
    checked = _bea(linked, "--json", "check")
    assert checked.returncode == 0, checked.stderr
    target = json.loads(checked.stdout)["target"]["file"]

    assert target == str(linked / "main.bean")
    assert _bea(linked, "--file", target, "check").returncode == 0


def test_a_write_to_the_root_names_the_link_too(linked: Path) -> None:
    result = _bea(linked, "--json", "add", "note", "--date", "2026-01-06", "-a", "Assets:Cash", "-m", "hi")

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["target"] == {"file": str(linked / "main.bean"), "into": str(linked / "main.bean")}


def test_format_target_files_name_the_link(linked: Path) -> None:
    """`format --check` reports the root as named, not its resolved target (w5/795)."""
    aligned = _bea(linked, "format", "-i", "main.bean")
    assert aligned.returncode == 0, aligned.stderr

    checked = _bea(linked, "--json", "format", "--check", "main.bean")

    assert checked.returncode == 0, checked.stderr
    files = json.loads(checked.stdout)["target"]["files"]
    assert files == [str(linked / "inc.bean"), str(linked / "main.bean")]
    assert _bea(linked, "--json", "format", "--check", files[1]).returncode == 0


def test_text_add_names_the_link_like_json(linked: Path) -> None:
    """The text confirmation uses the `write_target` path, not the engine's resolved one (w5/795)."""
    result = _bea(linked, "add", "note", "--date", "2026-01-06", "-a", "Assets:Cash", "-m", "hi")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"Added 1 note to {linked / 'main.bean'}."
