"""`doctor roundtrip`'s scratch copies of the ledger are private (w5/457).

Upstream writes a full printed copy of the ledger to `main.roundtrip1.bean`
(and `…2`) with the process umask, so a `0600` ledger was copied out
world-readable for the length of the run.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
# The plugin runs while upstream loads the ledger, after bea has prepared the
# scratch names and before upstream writes into them: it records what is there.
PROBE = """import os, stat
__plugins__ = ["probe"]
def probe(entries, options):
    here = os.path.dirname(os.path.realpath(options["filename"]))
    path = os.path.join(here, "main.roundtrip1.bean")
    with open(os.path.join(here, "mode.txt"), "w") as out:
        out.write(oct(stat.S_IMODE(os.stat(path).st_mode)) if os.path.exists(path) else "absent")
    return entries, []
"""
LEDGER = """option "insert_pythonpath" "TRUE"
plugin "probe_plugin"
2026-01-01 open Assets:Cash USD
"""


@pytest.mark.skipif(os.name != "posix", reason="POSIX file modes")
def test_the_scratch_copy_is_private_and_removed(tmp_path: Path) -> None:
    (tmp_path / "probe_plugin.py").write_text(PROBE)
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    ledger.chmod(0o600)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "doctor", "roundtrip", str(ledger)],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
        preexec_fn=lambda: os.umask(0o022),
    )
    assert result.returncode == 0, result.stderr
    assert "Congratulations" in result.stderr
    assert (tmp_path / "mode.txt").read_text() == "0o600"
    assert not (tmp_path / "main.roundtrip1.bean").exists()
    assert not (tmp_path / "main.roundtrip2.bean").exists()
