"""`bea example -o FILE --version` prints the version and writes nothing (w5/415).

bea writes bean-example's stdout to `-o` whenever it exits 0, and
`--version` exits 0 with a one-line banner: `ex.bean` became `Beancount
3.2.3`, and with `--force` an existing ledger was replaced by it.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.commands import example as example_command
from cli.main import app

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n'


def _bea(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(cwd / "config"),
        XDG_CACHE_HOME=str(cwd / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def test_version_with_output_prints_and_creates_nothing(tmp_path: Path) -> None:
    result = _bea(tmp_path, "example", "--seed", "1", "-o", "ex.bean", "--version")
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("Beancount ")
    assert "ex.bean was not written" in result.stderr
    assert not (tmp_path / "ex.bean").exists()


def test_version_with_force_leaves_the_ledger(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    result = _bea(tmp_path, "example", "-o", "main.bean", "--force", "--version")
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "main.bean").read_text() == LEDGER


def test_output_without_a_ledger_is_never_written(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def banner(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], 0, "bean-example 9.9\n", "")

    monkeypatch.setattr(example_command.launch, "capture_native", banner)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(app, ["example", "-o", "ex.bean"])

    assert result.exit_code == 1
    assert "bean-example printed no ledger, so ex.bean was not written." in result.stderr
    assert not (tmp_path / "ex.bean").exists()
