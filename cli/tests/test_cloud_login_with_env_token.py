"""`bea cloud login` refuses while `BEA_TOKEN` is set (w5/516).

`BEA_TOKEN` takes precedence over the stored file unconditionally, so a login
printed "Logged in successfully." and every later command still sent the
revoked token.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _login(tmp_path: Path, token: str, *flags: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        # Nothing listens here: a refusal must come before any request.
        BEA_API_URL="http://127.0.0.1:9",
        BEA_TOKEN=token,
        BROWSER="/usr/bin/true",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *flags, "cloud", "login"],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_login_refuses_while_the_token_is_set(tmp_path: Path) -> None:
    result = _login(tmp_path, "stale-token")

    assert result.returncode == 2, result.stdout + result.stderr
    assert "BEA_TOKEN is set in this shell and takes precedence over a login" in result.stderr
    assert "Logged in successfully" not in result.stdout + result.stderr
    assert not (tmp_path / "config" / "credentials.json").exists()


def test_an_empty_token_is_unset(tmp_path: Path) -> None:
    result = _login(tmp_path, "", "--no-input")

    assert result.returncode == 2
    assert "Login needs a browser and a terminal" in result.stderr
    assert "takes precedence" not in result.stderr
