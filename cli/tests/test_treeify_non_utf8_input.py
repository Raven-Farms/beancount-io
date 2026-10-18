"""`bea treeify` refuses non-UTF-8 input in bea's words, file or stdin (w5/535).

Upstream decodes strictly and crashed on Latin-1 text, which bea reported as
`treeify failed (exit 1): UnicodeDecodeError: …`, where `format -` names the
input and the byte and says to re-save it as UTF-8.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LATIN1 = b"Assets:Caf\xe9 10 EUR\nAssets:Bank 5 EUR\n"


def _treeify(tmp_path: Path, args: list[str], stdin: bytes | None) -> subprocess.CompletedProcess[bytes]:
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
        [sys.executable, "-m", "cli.main", "treeify", *args],
        cwd=tmp_path,
        env=env,
        input=stdin if stdin is not None else b"",
        capture_output=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize(("args", "named"), [(["t1.txt"], "t1.txt"), ([], "stdin")], ids=["file", "stdin"])
def test_non_utf8_input_is_refused_with_the_shared_message(tmp_path: Path, args: list[str], named: str) -> None:
    (tmp_path / "t1.txt").write_bytes(LATIN1)

    result = _treeify(tmp_path, args, None if args else LATIN1)

    assert result.returncode == 2, result.stderr
    message = result.stderr.decode()
    assert f"Cannot decode '{named}' as UTF-8: invalid continuation byte at byte 10." in message
    assert "UnicodeDecodeError" not in message


def test_utf8_stdin_still_renders(tmp_path: Path) -> None:
    result = _treeify(tmp_path, [], "Assets:Café 10 EUR\nAssets:Bank 5 EUR\n".encode())

    assert result.returncode == 0, result.stderr
    assert "Café 10 EUR" in result.stdout.decode()
