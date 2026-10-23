"""A stored token bea could not have saved is an unusable file, which logout removes (w5/811).

With `"token": ""` the file read as "Not logged in", and with a token holding
whitespace, a tab or a non-ASCII letter as "Invalid … stored credential";
either way `cloud logout` exited 3 and left the file on disk. A
`BEA_CONFIG_DIR` that is a symbolic-link loop was blamed on the credential.
Nothing here reaches the network.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOKENS = {
    "empty": ("", "its token is empty"),
    "space": ("qa fake", "its token contains whitespace, control or non-ASCII characters"),
    "tab": ("qa\tfake", "its token contains whitespace, control or non-ASCII characters"),
    "non-ascii": ("qa-fäke", "its token contains whitespace, control or non-ASCII characters"),
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


@pytest.mark.parametrize("case", sorted(TOKENS))
def test_status_names_the_file_and_logout_removes_it(tmp_path: Path, case: str) -> None:
    token, reason = TOKENS[case]
    config = tmp_path / "cfg"
    config.mkdir(mode=stat.S_IRWXU)
    stored = config / "credentials.json"
    stored.write_text(json.dumps({"token": token, "expireAt": "2099-01-01T00:00:00+00:00"}))

    status = _bea(config, "cloud", "status")

    assert status.returncode == 3, status.stderr
    message = " ".join(status.stderr.split())
    assert f"The stored credential {stored} is unusable: {reason}." in message
    assert "Not logged in" not in message
    assert stored.exists()

    logout = _bea(config, "cloud", "logout")

    assert logout.returncode == 1, logout.stderr
    assert f"Removed the unusable credential file {stored}" in " ".join(logout.stderr.split())
    assert not stored.exists()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX symbolic links")
def test_a_config_directory_loop_is_blamed_on_the_directory(tmp_path: Path) -> None:
    loop = tmp_path / "cfgloop"
    loop.symlink_to(loop)

    status = _bea(loop, "cloud", "status")

    assert status.returncode == 3, status.stderr
    message = " ".join(status.stderr.split())
    assert f"The bea configuration directory {loop} cannot be used" in message
    assert "Point BEA_CONFIG_DIR at a directory" in message
    assert "stored credential" not in message
