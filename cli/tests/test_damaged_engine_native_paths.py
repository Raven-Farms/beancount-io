"""A damaged managed engine is named with its remedy on every path (w5/785).

w5/320 taught the helper paths to report a damaged engine, but text `check`
swallowed that error as `portable`, native runs never probed, and `engine
enable` installed into the breakage (or blamed the feature). The damaged
message is now an `EngineError` the fail-open handlers re-raise, native
failures probe before reporting, and `enable` probes its base.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = "2026-01-01 open Assets:Cash USD\n"
DAMAGE = "ImportError: cannot import name '_parser' from 'beancount.parser'"
TRACEBACK = f'Traceback (most recent call last):\n  File "<frozen importlib>", line 1, in <module>\n{DAMAGE}\n'


def _damaged_python(directory: Path) -> None:
    binary = directory / "bin" / "python"
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_text(f"#!{sys.executable}\nimport sys\nsys.stderr.write({TRACEBACK!r})\nraise SystemExit(1)\n")
    binary.chmod(0o755)


def _healthy_python(directory: Path) -> None:
    binary = directory / "bin" / "python"
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_text(
        f"#!{sys.executable}\nimport os, sys\nos.execv({sys.executable!r}, [{sys.executable!r}, *sys.argv[1:]])\n"
    )
    binary.chmod(0o755)


def _crashing_native(directory: Path, name: str, log: Path) -> None:
    script = directory / "bin" / name
    script.write_text(
        f"#!{sys.executable}\nimport sys\n"
        f"with open({str(log)!r}, 'a') as out:\n    out.write({name!r} + '\\n')\n"
        f"sys.stderr.write({TRACEBACK!r})\nraise SystemExit(1)\n"
    )
    script.chmod(0o755)


def _fake_engine(directory: Path, *, damaged: bool) -> Path:
    """A managed engine layout whose interpreter (cannot) load, and whose natives crash."""
    root = directory / "managed" / "engine"
    (_damaged_python if damaged else _healthy_python)(root)
    for package in ("beancount", "beanquery"):
        (root / "lib" / "python3.12" / "site-packages" / package).mkdir(parents=True)
    log = directory / "native-ran.log"
    for name in ("bean-check", "bean-doctor", "bean-example"):
        _crashing_native(root, name, log)
    return root


def _env(directory: Path, engine: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(directory / "config"),
        XDG_CACHE_HOME=str(directory / "cache"),
        BEA_ENGINE_DIR=str(engine),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
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


def _assert_damaged(result: subprocess.CompletedProcess[str], engine: Path) -> None:
    assert result.returncode == 1, result.stdout + result.stderr
    assert "is damaged and cannot load" in result.stderr
    assert f"Remove {engine} and rerun" in result.stderr


@pytest.fixture
def damaged(tmp_path: Path) -> tuple[Path, Path]:
    (tmp_path / "main.bean").write_text(LEDGER)
    return tmp_path, _fake_engine(tmp_path, damaged=True)


@pytest.mark.parametrize("args", [["-f", "main.bean", "check"], ["-f", "main.bean", "check", "-v"]])
def test_check_names_the_damage_without_running_bean_check(damaged: tuple[Path, Path], args: list[str]) -> None:
    directory, engine = damaged
    result = _bea(directory, _env(directory, engine), *args)

    _assert_damaged(result, engine)
    assert "Traceback" not in result.stdout + result.stderr
    log = directory / "native-ran.log"
    ran = log.read_text() if log.exists() else ""
    assert "bean-check" not in ran


@pytest.mark.parametrize(
    ("args", "streamed"),
    [
        (("doctor", "lex", "main.bean"), False),
        (("doctor", "roundtrip", "main.bean"), False),
        (("doctor", "print-options", "main.bean"), False),
        (("doctor", "context", "main.bean", "1"), True),
    ],
)
def test_doctor_names_the_damage(damaged: tuple[Path, Path], args: tuple[str, ...], streamed: bool) -> None:
    directory, engine = damaged
    result = _bea(directory, _env(directory, engine), *args)

    _assert_damaged(result, engine)
    if not streamed:
        # Helper-first operations never run the native tool; streamed ones
        # cannot unprint its traceback, but still name the remedy.
        assert "Traceback" not in result.stdout + result.stderr


def test_example_names_the_damage(damaged: tuple[Path, Path]) -> None:
    directory, engine = damaged
    result = _bea(directory, _env(directory, engine), "-f", "main.bean", "example")

    _assert_damaged(result, engine)
    assert "bean-example failed" not in result.stderr


@pytest.mark.parametrize("feature", ["beangulp", "beanprice"])
def test_engine_enable_refuses_a_damaged_base(damaged: tuple[Path, Path], feature: str) -> None:
    directory, engine = damaged
    result = _bea(directory, _env(directory, engine), "engine", "enable", feature)

    _assert_damaged(result, engine)
    assert "ready." not in result.stderr
    assert not (engine / "bea-features.json").exists()


def test_a_healthy_engine_with_crashing_natives_falls_through(tmp_path: Path) -> None:
    """The probe gates the remedy: a traceback from a working engine keeps its old report."""
    (tmp_path / "main.bean").write_text(LEDGER)
    engine = _fake_engine(tmp_path, damaged=False)
    env = _env(tmp_path, engine)

    example = _bea(tmp_path, env, "-f", "main.bean", "example")
    assert example.returncode == 1, example.stdout + example.stderr
    assert "bean-example failed (exit 1)" in example.stderr
    assert "damaged" not in example.stdout + example.stderr

    context = _bea(tmp_path, env, "doctor", "context", "main.bean", "1")
    assert context.returncode == 1, context.stdout + context.stderr
    assert "Traceback" in context.stdout + context.stderr
    assert "damaged" not in context.stdout + context.stderr
