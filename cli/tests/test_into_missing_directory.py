"""`--into` a new file in a directory that does not exist is a usage refusal (w5/492).

The missing directory was noticed only when staging, and reported as an
internal failure to write a staged copy, exit 1 `validation`, so an agent
retried or blamed the ledger.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVENT = ("add", "event", "--date", "2026-01-05", "-t", "a", "-d", "b", "--into", "y/b/new.bean")


def _books(tmp_path: Path) -> Path:
    (tmp_path / "y" / "a").mkdir(parents=True)
    (tmp_path / "y" / "a" / "a.bean").write_text('2026-01-01 event "a" "x"\n')
    ledger = tmp_path / "main.bean"
    ledger.write_text('option "operating_currency" "USD"\ninclude "y/*/*.bean"\n')
    return ledger


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
        [sys.executable, "-m", "cli.main", "--json", "-f", str(tmp_path / "main.bean"), *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_a_missing_directory_is_a_usage_refusal(tmp_path: Path) -> None:
    _books(tmp_path)

    result = _bea(tmp_path, *EVENT)

    assert result.returncode == 2, result.stdout + result.stderr
    error = json.loads(result.stdout or result.stderr)["error"]
    assert error["category"] == "usage"
    assert f"directory {tmp_path.resolve() / 'y' / 'b'} does not exist. Create it first" in error["message"]
    assert "staged copy" not in error["message"]
    assert not (tmp_path / "y" / "b").exists()


def test_a_file_in_the_way_is_named(tmp_path: Path) -> None:
    _books(tmp_path)
    (tmp_path / "y" / "b").write_text("")

    result = _bea(tmp_path, *EVENT)

    assert result.returncode == 2, result.stdout + result.stderr
    assert "is not a directory" in json.loads(result.stdout or result.stderr)["error"]["message"]


def test_an_existing_directory_takes_the_new_file(tmp_path: Path) -> None:
    _books(tmp_path)
    (tmp_path / "y" / "b").mkdir()

    result = _bea(tmp_path, *EVENT)

    assert result.returncode == 0, result.stderr
    assert '2026-01-05 event "a" "b"' in (tmp_path / "y" / "b" / "new.bean").read_text()
