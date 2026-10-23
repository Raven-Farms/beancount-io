"""An engine probe a resource limit keeps from starting says nothing about the engine (w5/815).

Under `ulimit -n 9`, `engine status` called a working managed engine "damaged
— the engine cannot load ([Errno 24] Too many open files)" and advised
removing it, though `check` ran under the same limit; a process limit made
its features read "absent" too. The probe never ran, so the answer is unknown.
"""

from __future__ import annotations

import errno
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.engine import launch, paths, provision
from cli.main import app

runner = CliRunner()
_RUN = subprocess.run


def _refuse_probes(monkeypatch: pytest.MonkeyPatch, number: int) -> None:
    """Every `python -P -c …` probe is refused the way a process or descriptor limit refuses it."""

    def run(command: Any, *args: Any, **kwargs: Any) -> Any:
        if list(command)[1:3] == ["-P", "-c"]:
            raise OSError(number, os.strerror(number))
        return _RUN(command, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", run)


def _managed(monkeypatch: pytest.MonkeyPatch) -> Path:
    """A provisioned managed engine whose interpreter is this one."""
    root: Path = paths.engine_root()
    monkeypatch.setattr(paths, "is_provisioned", lambda _root: True)
    monkeypatch.setattr(launch, "resolve_engine", lambda: launch.EngineSource("managed", root, Path(sys.executable)))
    return root


@pytest.mark.parametrize("number", [errno.EMFILE, errno.EAGAIN], ids=["EMFILE", "EAGAIN"])
def test_a_managed_engine_that_could_not_be_probed_gets_no_removal_advice(
    tmp_path: Path, bea_config_dir: Path, monkeypatch: pytest.MonkeyPatch, number: int
) -> None:
    root = _managed(monkeypatch)
    _refuse_probes(monkeypatch, number)

    text = runner.invoke(app, ["engine", "status"])
    structured = runner.invoke(app, ["--json", "engine", "status"])

    assert text.exit_code == 0, text.output
    assert "damaged" not in text.stdout and f"Remove {root}" not in text.stdout
    assert f"whether it loads is unknown — the check could not start ({os.strerror(number)}:" in text.stdout
    data = json.loads(structured.stdout)["data"]
    assert data["usable"] is None
    assert "damaged" not in data
    assert data["unchecked"].startswith("the check could not start")


def test_an_unprobed_feature_reads_unknown_not_absent(
    tmp_path: Path, bea_config_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    override = tmp_path / "python3"
    override.symlink_to(sys.executable)
    monkeypatch.setenv("BEA_ENGINE_PYTHON", str(override))
    _refuse_probes(monkeypatch, errno.EAGAIN)

    status = provision.feature_status()

    assert status["features"], "the manifest defines optional features"
    assert {info["present"] for info in status["features"].values()} == {None}
    text = runner.invoke(app, ["engine", "status"])
    assert text.exit_code == 0, text.output
    assert ", absent (" not in text.stdout
    assert ", unknown (" in text.stdout
    assert "Usable: unknown — the check could not start" in text.stdout


def test_a_probe_that_ran_and_failed_is_still_damaged(
    tmp_path: Path, bea_config_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _managed(monkeypatch)
    monkeypatch.setattr(launch, "engine_load_failure", lambda _python: "No module named 'beancount'")

    text = runner.invoke(app, ["engine", "status"])

    assert text.exit_code == 0, text.output
    assert f"Provisioned: damaged — the engine cannot load (No module named 'beancount'). Remove {root}" in text.stdout
