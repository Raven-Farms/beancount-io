"""`price export` refuses two different `--output` values (w5/483).

It parsed its own arguments and kept the last value: `-o first -o second`
exported to `second` alone with exit 0, where every other command refuses
two values for one option.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _export(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text('option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n')
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", "main.bean", "price", "export", *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize(
    ("args", "named"),
    [
        (("-o", "first", "-o", "second"), "-o 'first' and -o 'second'"),
        (("--output=first", "-o", "second"), "--output 'first' and -o 'second'"),
        (("--output", "first", "--output=second"), "--output 'first' and --output 'second'"),
    ],
)
def test_two_different_outputs_are_refused(tmp_path: Path, args: tuple[str, ...], named: str) -> None:
    result = _export(tmp_path, *args)

    assert result.returncode == 2, result.stdout + result.stderr
    assert f"Conflicting values for one option: {named}. Pass it once." in result.stderr
    assert not (tmp_path / "first").exists() and not (tmp_path / "second").exists()


def test_the_same_output_twice_is_accepted(tmp_path: Path) -> None:
    result = _export(tmp_path, "-o", "snap", "--output", "snap")

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "snap" / "main.bean").is_file()
