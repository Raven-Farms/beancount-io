"""A present but unusable `credentials.json` is named, not read as logged out (w5/297).

`load_credentials` swallowed every exception, so a file at mode 000, invalid
JSON or one missing `expireAt` gave `Not logged in`, and `bea cloud logout`
said `Already logged out.` with exit 0 while the token stayed on disk.
Nothing here reaches the network.
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

BAD_FILES = {
    "unreadable": ('{"token": "qa-fake", "expireAt": "2099-01-01T00:00:00Z"}', 0o000, "cannot be read"),
    "not-json": ("{not json", 0o600, "not valid JSON"),
    "no-expiry": ('{"token": "qa-fake"}', 0o600, "expireAt is missing"),
    "not-an-object": ("[]", 0o600, "not a JSON object"),
}


def _bea(config: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(config),
        XDG_CACHE_HOME=str(config.parent / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_API_URL="http://127.0.0.1:9",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", *args],
        env=env,
        cwd=config.parent,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads a mode-000 file")
@pytest.mark.parametrize("case", sorted(BAD_FILES))
def test_status_names_the_file_and_logout_removes_it(tmp_path: Path, case: str) -> None:
    text, mode, reason = BAD_FILES[case]
    config = tmp_path / "cfg"
    config.mkdir(mode=stat.S_IRWXU)
    stored = config / "credentials.json"
    stored.write_text(text)
    stored.chmod(mode)

    status = _bea(config, "cloud", "status")
    assert status.returncode == 3, status.stderr
    message = " ".join(status.stderr.split())
    assert str(stored) in message and reason in message
    assert "Not logged in" not in message

    logout = _bea(config, "cloud", "logout")
    assert logout.returncode == 1, logout.stdout + logout.stderr
    assert "Already logged out" not in logout.stdout + logout.stderr
    assert "Removed the unusable credential file" in " ".join(logout.stderr.split())
    assert not stored.exists()


def test_without_a_file_logout_is_still_a_no_op(tmp_path: Path) -> None:
    config = tmp_path / "cfg"
    config.mkdir(mode=stat.S_IRWXU)
    result = _bea(config, "cloud", "logout")
    assert result.returncode == 0, result.stderr
    assert "Already logged out." in result.stdout + result.stderr
