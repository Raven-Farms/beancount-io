"""A forwarded `-o ''` is refused naming the option, not read as absent (w5/389).

`forwarded_option` ended `return value or None`, so `example -o ''` skipped
bea's output guards and upstream failed with `Could not open file ''`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("args", "named"),
    [
        (("example", "--seed", "1", "-o", ""), "--output '' is empty"),
        (("example", "--seed", "1", "--output="), "--output '' is empty"),
        (("ingest", "extract", "--config", "run.py", "-o", "", "."), "--output '' is empty"),
        (("ingest", "extract", "--config", "run.py", "-e", "", "."), "--existing '' is empty"),
    ],
    ids=["example-o", "example-output-equals", "ingest-output", "ingest-existing"],
)
def test_an_empty_forwarded_path_is_refused(tmp_path: Path, args: tuple[str, ...], named: str) -> None:
    (tmp_path / "run.py").write_text("import beangulp\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    before = sorted(path.name for path in tmp_path.iterdir())

    result = subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )

    assert result.returncode == 2, result.stdout + result.stderr
    assert named in result.stderr
    assert "Could not open file" not in result.stderr
    assert sorted(path.name for path in tmp_path.iterdir() if path.name not in {"config", "cache"}) == [
        name for name in before if name not in {"config", "cache"}
    ]
