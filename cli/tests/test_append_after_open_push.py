"""An append after an unclosed `pushtag`/`pushmeta` is refused (w5/464).

Under `--allow-errors` the file's `Unbalanced pushed tag` was tolerated as
pre-existing, so the appended entry silently inherited `#trip` and
`source: "bank-a"` while the JSON echo showed it with neither.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAIN = """option "operating_currency" "USD"
include "inc.bean"
2026-01-01 open Assets:Cash USD
2026-01-01 open Equity:O USD
"""
ENTRY = """2026-01-02 * "A"
  Assets:Cash 1 USD
  Equity:O
"""


def _add(tmp_path: Path, inc: str, *flags: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(MAIN)
    (tmp_path / "inc.bean").write_text(inc)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "cli.main",
            *flags,
            "-f",
            str(tmp_path / "main.bean"),
            "add",
            "transaction",
            "B",
            "--date",
            "2026-01-03",
            "-p",
            "Assets:Cash 2 USD",
            "-p",
            "Equity:O",
            "--into",
            "inc.bean",
            "--allow-errors",
        ],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


OPEN = 'pushmeta source: "bank-a"\npushtag #trip\n' + ENTRY


@pytest.mark.parametrize("flags", [(), ("--json",)])
def test_an_append_inside_an_open_push_is_refused(tmp_path: Path, flags: tuple[str, ...]) -> None:
    result = _add(tmp_path, OPEN, *flags)
    assert result.returncode == 2, result.stderr
    message = json.loads(result.stdout or result.stderr)["error"]["message"] if flags else result.stderr
    assert "`pushtag #trip` at line 2" in message
    assert "`pushmeta source:` at line 1" in message
    assert (tmp_path / "inc.bean").read_text() == OPEN  # Nothing written.


def test_an_open_metadata_push_alone_is_refused(tmp_path: Path) -> None:
    inc = 'pushmeta source: "bank-a"\n' + ENTRY
    result = _add(tmp_path, inc)
    assert result.returncode == 2, result.stderr
    assert "`pushmeta source:` at line 1" in result.stderr
    assert (tmp_path / "inc.bean").read_text() == inc


def test_a_closed_push_still_takes_an_append(tmp_path: Path) -> None:
    inc = "pushtag #trip\n" + ENTRY + "poptag #trip\n"
    result = _add(tmp_path, inc)
    assert result.returncode == 0, result.stderr
    assert '2026-01-03 * "B"' in (tmp_path / "inc.bean").read_text()
