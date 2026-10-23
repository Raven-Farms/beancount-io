"""A resource limit that stops the engine or a native tool is named (w5/816).

When the OS refused to start the engine, every engine-backed command printed a
bare `[Errno 24] Too many open files` or `[Errno 35] Resource temporarily
unavailable`, naming neither the engine nor the limit. An engine the kernel
killed with SIGXCPU was blamed on "an out-of-memory killer, a timeout, or a
kill", none of which sends it.
"""

from __future__ import annotations

import errno
import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.engine import launch
from cli.errors import BeaError
from cli.main import app

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'option "operating_currency" "USD"\n2020-01-01 open Assets:Bank USD\n'


@pytest.mark.parametrize(
    ("number", "limit"),
    [
        (errno.EMFILE, "the open-file limit is reached (ulimit -n)"),
        (errno.EAGAIN, "the process limit is reached (ulimit -u)"),
    ],
    ids=["EMFILE", "EAGAIN"],
)
def test_a_refused_engine_spawn_names_the_engine_and_the_limit(
    tmp_path: Path, bea_config_dir: Path, monkeypatch: pytest.MonkeyPatch, number: int, limit: str
) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)

    def refuse(*_args: Any, **_kwargs: Any) -> None:
        raise OSError(number, os.strerror(number))

    monkeypatch.setattr(launch.subprocess, "Popen", refuse)

    result = CliRunner().invoke(app, ["--json", "-f", str(tmp_path / "main.bean"), "report", "balance-sheet"])

    assert result.exit_code == 1, result.output
    message = json.loads(result.stderr)["error"]["message"]
    assert message == f"Could not start the Beancount engine ({os.strerror(number)}: {limit}); nothing was run."


def test_a_refused_native_spawn_names_the_program(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: Any, **_kwargs: Any) -> None:
        raise OSError(errno.EMFILE, os.strerror(errno.EMFILE))

    monkeypatch.setattr(launch.subprocess, "Popen", refuse)

    with pytest.raises(BeaError) as caught:
        launch._popen(["/opt/engine/bin/bean-example", "--version"], stdout=subprocess.PIPE)

    assert str(caught.value).startswith("Could not start bean-example (")


def test_any_other_spawn_failure_is_left_as_it_was(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing(*_args: Any, **_kwargs: Any) -> None:
        raise FileNotFoundError(errno.ENOENT, "No such file or directory")

    monkeypatch.setattr(launch.subprocess, "Popen", missing)

    with pytest.raises(FileNotFoundError):
        launch._popen(["/nowhere/bean-example"], stdout=subprocess.PIPE)


@pytest.mark.skipif(not hasattr(signal, "SIGXCPU"), reason="POSIX resource-limit signals")
def test_an_engine_killed_by_sigxcpu_names_the_cpu_time_limit(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    wrapper = tmp_path / "engine-wrapper"
    wrapper.write_text(
        f"#!{sys.executable}\n"
        "import os, signal, sys\n"
        f"python = {sys.executable!r}\n"
        "if sys.argv[1:3] == ['-P', '-c']:\n"
        "    os.execv(python, [python, *sys.argv[1:]])\n"
        "os.kill(os.getpid(), signal.SIGXCPU)\n"
    )
    wrapper.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_ENGINE_PYTHON=str(wrapper),
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )

    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "-f", str(tmp_path / "main.bean"), "report", "balance-sheet"],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert result.returncode != 0
    error = json.loads(result.stderr)["error"]
    text = " ".join([error["message"], *error.get("details", []), str(error.get("hint", ""))])
    assert "SIGXCPU" in text
    assert "CPU-time limit (ulimit -t, RLIMIT_CPU)" in text
    assert "out-of-memory killer" not in text
