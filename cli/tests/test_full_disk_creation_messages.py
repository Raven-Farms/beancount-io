"""A full disk at creation is said in bea's words, and `init` leaves no directories behind (w5/610).

The frontend export writer caught only `PermissionError` when creating its
staged copy, so a full disk fell through to the stdout sentence, "Could not
write output: No space left on device", naming no file. `init` printed a
raw `OSError: [Errno 28]` when `mkdir` failed. When the ledger could not be
written it said nothing was written, but kept the directories it had made.
"""

from __future__ import annotations

import errno
import os
import resource
import signal
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bea_engine import initiating, protocol
from cli.main import app

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX resource limits")


def test_init_that_cannot_write_removes_the_directories_it_made(tmp_path: Path) -> None:
    def no_file_size() -> None:
        signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
        resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))

    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        PYTHONDONTWRITEBYTECODE="1",
        NO_COLOR="1",
    )
    for directory in ("config", "cache"):
        (tmp_path / directory).mkdir()
    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "init", "deep/er/main.bean", "--currency", "USD", "--date", "2026-01-01"],
        cwd=tmp_path,
        env=env,
        preexec_fn=no_file_size,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert result.returncode == 1, result.stderr
    expected = (
        f"Cannot write a staged copy of main.bean in {tmp_path / 'deep' / 'er'} (File too large); nothing was written."
    )
    assert expected in result.stderr
    assert not (tmp_path / "deep").exists()


def test_init_on_a_full_disk_says_so_and_removes_what_it_made(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real_mkdir = os.mkdir

    def mkdir(path: str | Path, mode: int = 0o777, *args: object, **kwargs: object) -> None:
        if Path(path).name == "books":
            raise OSError(errno.ENOSPC, os.strerror(errno.ENOSPC), str(path))
        real_mkdir(path, mode)

    monkeypatch.setattr(os, "mkdir", mkdir)
    ledger = tmp_path / "n1" / "books" / "main.bean"

    with pytest.raises(protocol.LedgerError) as raised:
        initiating.answer(ledger, currency="USD", date="2026-01-01")

    assert str(raised.value) == f"Cannot create {ledger.parent} (No space left on device); nothing was written."
    assert not (tmp_path / "n1").exists()


def test_an_export_whose_copy_the_disk_refuses_names_the_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "main.bean").write_text("2026-01-01 open Assets:Cash USD\n")
    out = tmp_path / "out.bean"
    real_open = os.open

    def full(path: str | Path, flags: int, mode: int = 0o777, *args: object, **kwargs: object) -> int:
        if Path(path).name.startswith(".bea-"):
            raise OSError(errno.ENOSPC, os.strerror(errno.ENOSPC), str(path))
        return real_open(path, flags, mode)

    monkeypatch.setattr(os, "open", full)

    result = CliRunner().invoke(app, ["format", str(tmp_path / "main.bean"), "-o", str(out)])

    assert result.exit_code == 1, result.output
    assert f"Cannot write {out} (No space left on device); nothing was written." in result.stderr
    assert "Could not write output" not in result.stderr
    assert not out.exists()
