"""Encrypted roots cannot hide terminating plugins from doctor preflights (w5/674)."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _env(directory: Path) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_") and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    env.update(
        PATH=f"{directory / 'bin'}{os.pathsep}{os.environ['PATH']}",
        PYTHONPATH=os.pathsep.join([str(ROOT / "src"), str(directory)]),
        BEA_CONFIG_DIR=str(directory / "config"),
        BEA_ENGINE_DIR=str(directory / "engine"),
        BEA_NO_UPDATE_NOTIFIER="1",
        XDG_CACHE_HOME=str(directory / "cache"),
        XDG_DATA_HOME=str(directory / "data"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return env


@pytest.mark.parametrize("code", [0, 7])
@pytest.mark.parametrize("operation", ["missing-open", "roundtrip"])
def test_doctor_detects_a_terminating_plugin_inside_an_encrypted_root(
    tmp_path: Path, code: int, operation: str
) -> None:
    (tmp_path / "bin").mkdir()
    root = tmp_path / "main.bean.gpg"
    root.write_bytes(b"opaque synthetic ciphertext")
    plain = tmp_path / "plain.txt"
    plain.write_text('plugin "hiddenplug"\n2026-01-01 open Assets:Cash USD\n2026-01-02 note Assets:Cash "secret"\n')
    gpg = tmp_path / "bin/gpg"
    gpg.write_text(f"#!/bin/sh\nexec /bin/cat {shlex.quote(str(plain))}\n")
    gpg.chmod(0o755)
    (tmp_path / "hiddenplug.py").write_text(
        "from pathlib import Path\n"
        '__plugins__ = ("run",)\ndef run(entries, options):\n'
        f'    Path(__file__).with_name("plugin-ran.txt").write_text("{code}")\n'
        f"    raise SystemExit({code})\n"
    )
    before = (root.read_bytes(), plain.read_bytes())

    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "doctor", operation, str(root)],
        cwd=tmp_path,
        env=_env(tmp_path),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stdout == ""
    assert 'Plugin "hiddenplug" failed while running:' in result.stderr
    assert f"SystemExit: {code}" in result.stderr
    assert "Congratulations" not in result.stderr
    assert "engine did not answer" not in result.stderr
    assert "outcome is unknown" not in result.stderr
    assert (tmp_path / "plugin-ran.txt").read_text() == str(code)
    assert (root.read_bytes(), plain.read_bytes()) == before


def test_plugin_exit_detection_uses_metadata_instead_of_exception_message_text() -> None:
    from beancount.loader import LoadError

    from bea_engine.managed_load import is_plugin_exit

    error = LoadError(
        {"filename": "<load>", "lineno": 0},
        'Error applying plugin "ordinary": ValueError: SystemExit should not terminate',
    )
    assert not is_plugin_exit(error)


def test_a_value_error_mentioning_system_exit_still_allows_a_lenient_read(tmp_path: Path) -> None:
    root = tmp_path / "main.bean"
    root.write_text(
        'plugin "ordinary"\n'
        "2026-01-01 open Assets:Cash USD\n"
        "2026-01-01 open Equity:Opening USD\n"
        '2026-01-02 * "Opening"\n  Assets:Cash 73 USD\n  Equity:Opening\n'
    )
    (tmp_path / "ordinary.py").write_text(
        '__plugins__ = ("run",)\ndef run(entries, options):\n    raise ValueError("SystemExit should not terminate")\n'
    )
    before = root.read_bytes()

    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "--json", "--file", str(root), "balance", "--allow-errors"],
        cwd=tmp_path,
        env=_env(tmp_path),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["data"]["assets"]["children"][0]["balance"] == {"USD": "73"}
    assert "ValueError: SystemExit should not terminate" in result.stdout + result.stderr
    assert root.read_bytes() == before
