"""`bea add custom --help` keeps one `--value` example per line (w5/307).

Click re-wrapped the Examples paragraph into one run-on line, which could
break between `--value` and its quoted argument.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = [
    "--value 'text:hello'",
    "--value 'number:1000'",
    "--value 'amount:500 USD'",
    "--value 'account:Assets:Cash'",
]


@pytest.mark.parametrize("columns", ["60", "120"])
def test_each_example_is_its_own_line(tmp_path: Path, columns: str) -> None:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        COLUMNS=columns,
        TERM="dumb",
        NO_COLOR="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "add", "custom", "--help"],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 0, result.stderr
    lines = [line.strip() for line in result.stdout.splitlines()]
    for example in EXAMPLES:
        assert example in lines, result.stdout
