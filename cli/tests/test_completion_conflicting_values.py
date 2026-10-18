"""TAB completion never raises on an option given two different values (w5/646).

The single-value parser refused the conflict even while Click parsed
resiliently for completion, so a TAB after `-f main.bean -f other.bean`
printed an 11 MB traceback (completion sets a 100,000-column terminal) and
offered nothing.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _complete(tmp_path: Path, words: str) -> subprocess.CompletedProcess[str]:
    for name in ("main.bean", "other.bean"):
        (tmp_path / name).write_text("2026-01-01 open Assets:Cash USD\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("BEA_", "_TYPER"))}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        _TYPER_COMPLETE_ARGS=words,
        _BEA_COMPLETE="complete_zsh",
    )
    return subprocess.run(
        [sys.executable, "-c", "import sys; from cli.entry import main; sys.argv[0] = 'bea'; main()"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        stdin=subprocess.DEVNULL,
        check=False,
    )


@pytest.mark.parametrize(
    ("words", "offered"),
    [
        ("bea -f main.bean -f other.bean ad", '"add":'),
        ("bea -f main.bean add transaction --date 2026-01-01 --date 2026-01-02 --pa", '"--payee":'),
    ],
    ids=["global-file", "command-option"],
)
def test_completion_offers_candidates_silently(tmp_path: Path, words: str, offered: str) -> None:
    result = _complete(tmp_path, words)

    assert result.returncode == 0, result.stderr[:500]
    assert offered in result.stdout
    assert result.stderr == ""
