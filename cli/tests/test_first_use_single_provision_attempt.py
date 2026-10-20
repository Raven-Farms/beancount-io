"""A failed first-use provision fails the command once, not twice (w5/784).

Text `check` and `doctor` swallowed the helper's provisioning failure in a
fail-open handler, provisioned again for the native run, and — when the retry
succeeded — still exited 1 with the stale failure. Provisioning failures are
an `EngineError` those handlers do not catch: one attempt, one error.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from cli.commands import doctor
from cli.errors import BeaError, EngineError

ROOT = Path(__file__).resolve().parents[1]
LEDGER = "2026-01-01 open Assets:Cash USD\n"
PLUGIN_LEDGER = '2026-01-01 open Assets:Cash USD\nplugin "missing_plugin_xyz"\n'
INSTALLED_CONTEXT = (
    "from pathlib import Path\nfrom cli.engine import paths\n"
    "paths.checkout_source_root = lambda: None\n"
    f"paths.helper_source_root = lambda: Path({str(ROOT / 'src')!r})\n"
)


def _failing_uv(directory: Path) -> Path:
    shim = directory / "fake-uv"
    shim.write_text(f"#!{sys.executable}\nimport sys\nprint('shim uv refuses', file=sys.stderr)\nraise SystemExit(1)\n")
    shim.chmod(0o755)
    return shim


def _first_use_env(directory: Path) -> dict[str, str]:
    bootstrap = directory / "bootstrap"
    bootstrap.mkdir(exist_ok=True)
    (bootstrap / "sitecustomize.py").write_text(INSTALLED_CONTEXT)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(directory / "config"),
        XDG_CACHE_HOME=str(directory / "cache"),
        BEA_ENGINE_DIR=str(directory / "managed" / "engine"),
        BEA_UV=str(_failing_uv(directory)),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=os.pathsep.join([str(bootstrap), str(ROOT / "src")]),
        TERM="dumb",
        NO_COLOR="1",
    )
    return env


def _bea(directory: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=directory,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def _attempts(result: subprocess.CompletedProcess[str]) -> int:
    return result.stderr.count("Installing the Beancount engine")


def test_check_makes_one_provision_attempt(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    result = _bea(tmp_path, _first_use_env(tmp_path), "-f", "main.bean", "check")

    assert result.returncode == 1, result.stdout + result.stderr
    assert _attempts(result) == 1, result.stderr
    assert "Could not create the engine environment" in result.stderr


@pytest.mark.parametrize(
    ("ledger", "args"),
    [
        (LEDGER, ("doctor", "parse", "main.bean")),
        (PLUGIN_LEDGER, ("doctor", "print-options", "main.bean")),
        (LEDGER, ("doctor", "print-options", "main.bean")),
    ],
    ids=["syntax-errors-of", "refuse-plugin-failures", "closure-syntax-errors-of"],
)
def test_doctor_makes_one_provision_attempt(tmp_path: Path, ledger: str, args: tuple[str, ...]) -> None:
    (tmp_path / "main.bean").write_text(ledger)
    result = _bea(tmp_path, _first_use_env(tmp_path), *args)

    assert result.returncode == 1, result.stdout + result.stderr
    assert _attempts(result) == 1, result.stderr
    assert "Could not create the engine environment" in result.stderr


def test_engine_error_is_a_validation_error() -> None:
    assert issubclass(EngineError, BeaError)
    assert EngineError("synthetic").exit_code == 1


def _fail_engine(*args: Any, **kwargs: Any) -> Any:
    raise EngineError("synthetic")


def _fail_plain(*args: Any, **kwargs: Any) -> Any:
    raise BeaError("synthetic")


def test_syntax_helpers_propagate_a_provisioning_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    monkeypatch.setattr(doctor.launch, "helper_json", _fail_engine)

    with pytest.raises(EngineError):
        doctor._syntax_errors_of(str(tmp_path / "main.bean"))
    with pytest.raises(EngineError):
        doctor._closure_syntax_errors_of(str(tmp_path / "main.bean"))

    monkeypatch.setattr(doctor.launch, "helper_json", _fail_plain)
    assert doctor._syntax_errors_of(str(tmp_path / "main.bean")) == []
    assert doctor._closure_syntax_errors_of(str(tmp_path / "main.bean")) == []


def test_plugin_refusal_propagates_a_provisioning_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "main.bean").write_text(PLUGIN_LEDGER)
    monkeypatch.setattr(doctor.launch, "helper_json", _fail_engine)

    with pytest.raises(EngineError):
        doctor._refuse_plugin_failures("print-options", str(tmp_path / "main.bean"))

    monkeypatch.setattr(doctor.launch, "helper_json", _fail_plain)
    assert doctor._refuse_plugin_failures("print-options", str(tmp_path / "main.bean")) is None
