"""`bea treeify` refuses non-UTF-8 input in bea's words, file or stdin (w5/535).

Upstream decodes strictly and crashed on Latin-1 text, which bea reported as
`treeify failed (exit 1): UnicodeDecodeError: …`, where `format -` names the
input and the byte and says to re-save it as UTF-8. A BOM file rendered an
invisible second root, and Latin-1 through `/dev/stdin`, `<(…)` or a FIFO
still failed raw, because bea validated a file's bytes but upstream re-read
them (w5/723).
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LATIN1 = b"Assets:Caf\xe9 10 EUR\nAssets:Bank 5 EUR\n"
BOM_UTF8 = b"\xef\xbb\xbfAssets:Cafe 10 EUR\nAssets:Bank 5 EUR\n"


def _treeify(
    tmp_path: Path, args: list[str], stdin: bytes | None, *, pass_fds: tuple[int, ...] = ()
) -> subprocess.CompletedProcess[bytes]:
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
        pass_fds=pass_fds,
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


@pytest.mark.parametrize(("args", "named"), [(["bom.txt"], None), ([], "stdin")], ids=["file", "stdin"])
def test_a_bom_is_skipped_not_rendered(tmp_path: Path, args: list[str], named: str | None) -> None:
    (tmp_path / "bom.txt").write_bytes(BOM_UTF8)

    result = _treeify(tmp_path, args, BOM_UTF8 if named == "stdin" else None)

    assert result.returncode == 0, result.stderr
    shown = result.stdout.decode()
    assert shown.count("Assets") == 1, shown
    assert "Cafe 10 EUR" in shown and "Bank 5 EUR" in shown
    assert "Bank5 EUR" not in shown


@pytest.mark.skipif(sys.platform == "win32", reason="no /dev/stdin on Windows")
def test_a_piped_dev_stdin_is_refused_with_the_shared_message(tmp_path: Path) -> None:
    result = _treeify(tmp_path, ["/dev/stdin"], LATIN1)

    assert result.returncode == 2, result.stderr
    message = result.stderr.decode()
    assert "Cannot decode '/dev/stdin' as UTF-8: invalid continuation byte at byte 10." in message
    assert "UnicodeDecodeError" not in message


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no FIFOs on this platform")
def test_a_fifo_is_read_here_not_raw_by_upstream(tmp_path: Path) -> None:
    fifo = tmp_path / "flow"
    os.mkfifo(fifo)

    def feed() -> None:
        with open(fifo, "wb") as writer:
            writer.write(LATIN1)

    feeder = threading.Thread(target=feed, daemon=True)
    feeder.start()
    try:
        result = _treeify(tmp_path, ["flow"], None)
    finally:
        feeder.join(timeout=30)

    assert result.returncode == 2, result.stderr
    message = result.stderr.decode()
    assert "Cannot decode 'flow' as UTF-8: invalid continuation byte at byte 10." in message
    assert "UnicodeDecodeError" not in message


@pytest.mark.skipif(sys.platform == "win32", reason="no /dev/fd/N on Windows")
def test_a_held_descriptor_is_read_here_not_raw_by_upstream(tmp_path: Path) -> None:
    (tmp_path / "t1.txt").write_bytes(LATIN1)
    held = os.open(tmp_path / "t1.txt", os.O_RDONLY)
    try:
        result = _treeify(tmp_path, [f"/dev/fd/{held}"], None, pass_fds=(held,))
    finally:
        os.close(held)

    assert result.returncode == 2, result.stderr
    message = result.stderr.decode()
    assert f"Cannot decode '/dev/fd/{held}' as UTF-8: invalid continuation byte at byte 10." in message
    assert "UnicodeDecodeError" not in message


@pytest.mark.skipif(sys.platform == "win32", reason="no /dev/fd/N on Windows")
def test_a_held_descriptor_of_valid_text_still_renders(tmp_path: Path) -> None:
    (tmp_path / "ok.txt").write_text("Assets:Cafe 10 EUR\nAssets:Bank 5 EUR\n")
    held = os.open(tmp_path / "ok.txt", os.O_RDONLY)
    try:
        result = _treeify(tmp_path, [f"/dev/fd/{held}"], None, pass_fds=(held,))
    finally:
        os.close(held)

    assert result.returncode == 0, result.stderr
    shown = result.stdout.decode()
    assert "Cafe 10 EUR" in shown and "Bank 5 EUR" in shown
