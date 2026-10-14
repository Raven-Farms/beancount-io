"""A `BEA_ENGINE_PYTHON` that cannot load the helper is blamed by name (w5/269).

An override interpreter without Beancount died on the helper's first import.
`bea balance` printed the import traceback under "did not answer", never
naming the variable, and `bea add` exited 4 with "the outcome is unknown"
although no command had run.
"""

from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path

import pytest

from cli.engine import launch, paths
from cli.errors import ConflictError

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """\
option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD
"""
ADD = (
    "add",
    "transaction",
    "Lunch",
    "--date",
    "2026-01-05",
    "--posting",
    "Expenses:Food 4.00 USD",
    "--posting",
    "Assets:Cash",
)


@pytest.fixture(scope="module")
def bare_python(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """An interpreter of this version with no third-party packages, so no Beancount."""
    root = tmp_path_factory.mktemp("bare-engine")
    venv.create(root, with_pip=False, symlinks=sys.platform != "win32")
    return paths.venv_python(root)


@pytest.fixture
def ledger(tmp_path: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(LEDGER)
    return path


def _bea(tmp_path: Path, override: Path | None, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    if override is not None:
        env[paths.PYTHON_ENV] = str(override)
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _assert_names_the_override(result: subprocess.CompletedProcess[str], override: Path) -> None:
    assert result.returncode == 1, result.stderr
    assert result.stdout == ""
    assert f"{paths.PYTHON_ENV}={override} names an environment that cannot run the Beancount engine" in result.stderr
    assert f"Correct or unset {paths.PYTHON_ENV}" in result.stderr
    assert "outcome is unknown" not in result.stderr
    assert "did not answer" not in result.stderr


@pytest.mark.parametrize(
    "command",
    [("balance",), ("list", "open"), ("query", "SELECT account"), ("report", "balance-sheet")],
    ids=lambda command: command[0],
)
def test_a_read_names_the_variable_without_a_traceback(
    tmp_path: Path, ledger: Path, bare_python: Path, command: tuple[str, ...]
) -> None:
    result = _bea(tmp_path, bare_python, "-f", str(ledger), *command)

    _assert_names_the_override(result, bare_python)
    assert "Traceback" not in result.stderr
    assert len(result.stderr.strip().splitlines()) == 1


def test_a_write_that_never_started_is_a_plain_failure(tmp_path: Path, ledger: Path, bare_python: Path) -> None:
    result = _bea(tmp_path, bare_python, "-f", str(ledger), *ADD)

    _assert_names_the_override(result, bare_python)
    assert "Traceback" not in result.stderr
    assert ledger.read_text() == LEDGER


def test_json_mode_carries_the_same_message_and_no_traceback(tmp_path: Path, ledger: Path, bare_python: Path) -> None:
    result = _bea(tmp_path, bare_python, "--json", "-f", str(ledger), "balance")

    _assert_names_the_override(result, bare_python)
    assert "Traceback" not in result.stderr
    assert '"exit_code": 1' in result.stderr


def test_debug_shows_the_engine_traceback(tmp_path: Path, ledger: Path, bare_python: Path) -> None:
    result = _bea(tmp_path, bare_python, "--debug", "-f", str(ledger), "balance")

    _assert_names_the_override(result, bare_python)
    assert "Traceback (most recent call last)" in result.stderr
    assert "No module named 'beancount'" in result.stderr


def test_the_forwarded_tool_message_is_unchanged(tmp_path: Path, ledger: Path, bare_python: Path) -> None:
    result = _bea(tmp_path, bare_python, "-f", str(ledger), "check")

    assert result.returncode == 1
    assert f"{paths.PYTHON_ENV}={bare_python} names an environment with no 'bean-check'" in result.stderr
    assert f"Correct or unset {paths.PYTHON_ENV}" in result.stderr


def test_without_the_variable_the_same_commands_work(tmp_path: Path, ledger: Path) -> None:
    assert _bea(tmp_path, None, "-f", str(ledger), "balance").returncode == 0
    added = _bea(tmp_path, None, "-f", str(ledger), *ADD)
    assert added.returncode == 0, added.stderr
    assert "Lunch" in ledger.read_text()


def test_a_working_override_whose_writer_dies_is_still_an_unknown_outcome(monkeypatch: pytest.MonkeyPatch) -> None:
    """Only an interpreter that cannot load the helper proves nothing was written."""
    monkeypatch.setenv(paths.PYTHON_ENV, sys.executable)
    died = subprocess.CompletedProcess(["bea-engine"], 1, "", "boom\n")

    with pytest.raises(ConflictError, match="outcome is unknown"):
        launch._parse(died, ["add"], writes=True)
