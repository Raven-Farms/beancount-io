"""A SOCKS proxy in the environment is refused in bea's words, without pip advice (w5/518).

httpx builds a transport for every proxy in the environment when the client
is created and raised `ImportError` for a SOCKS one without `socksio`, even
for a host `no_proxy` excludes; bea passed on its "pip install httpx[socks]"
advice, which a Homebrew or `uv tool` install cannot follow.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _bea(tmp_path: Path, proxy: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text('option "operating_currency" "USD"\n')
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("BEA_") and k != "CI" and not k.lower().endswith("_proxy")
    }
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_API_URL="http://127.0.0.1:9",
        BEA_TOKEN="test-token-value",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
        **proxy,
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


@pytest.mark.parametrize(
    ("proxy", "named"),
    [
        ({"ALL_PROXY": "socks5://user:secret@127.0.0.1:1080"}, "ALL_PROXY"),
        ({"all_proxy": "socks5h://127.0.0.1:1080", "no_proxy": "127.0.0.1,localhost"}, "all_proxy"),
    ],
    ids=["ALL_PROXY", "all_proxy-with-no_proxy"],
)
@pytest.mark.parametrize(
    "args", [("cloud", "ledger", "list"), ("cloud", "status"), ("-f", "main.bean", "ask", "--print", "q")]
)
def test_a_socks_proxy_is_refused_naming_the_variable(
    tmp_path: Path, proxy: dict[str, str], named: str, args: tuple[str, ...]
) -> None:
    result = _bea(tmp_path, proxy, "--json", *args) if args[0] == "cloud" else _bea(tmp_path, proxy, *args)

    assert result.returncode == 2, result.stdout + result.stderr
    text = result.stdout + result.stderr
    assert f"{named} names a SOCKS proxy" in text
    assert "pip install" not in text
    assert "--debug" not in text
    assert "secret" not in text
    if args[0] == "cloud":
        assert json.loads(result.stdout or result.stderr)["error"]["category"] == "usage"
