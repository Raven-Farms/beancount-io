"""A managed engine whose packages are present but damaged is named, not trusted (w5/320).

`is_provisioned` checks only that the core package directories exist, so a
root whose contents were damaged (a quarantined compiled extension, a
half-deleted package) reported "Provisioned: yes", every command printed an
import traceback, and a write exited 4 "the outcome is unknown" although
nothing ran. The fixture is a root whose `beancount/` and `beanquery/` are
present but empty — the same failure as a missing `_parser` extension: the
interpreter cannot import the helper.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX venv layout")

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Checking USD\n'


@pytest.fixture(scope="module")
def damaged_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("engine") / "damaged"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(root)], check=True, capture_output=True)
    (site,) = root.glob("lib/python*/site-packages")
    for name in ("beancount", "beanquery"):
        (site / name).mkdir()
    return root


def _bea(tmp_path: Path, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_ENGINE_DIR=str(root),
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def test_status_reports_the_engine_damaged(tmp_path: Path, damaged_root: Path) -> None:
    text = _bea(tmp_path, damaged_root, "engine", "status")
    assert text.returncode == 0, text.stderr
    assert "Provisioned: damaged" in text.stdout and "Provisioned: yes" not in text.stdout
    as_json = _bea(tmp_path, damaged_root, "--json", "engine", "status")
    assert json.loads(as_json.stdout)["data"]["damaged"]


@pytest.mark.parametrize(
    "command", [("balance",), ("add", "note", "--date", "2026-01-05", "-a", "Assets:Checking", "-m", "x")]
)
def test_commands_name_the_root_and_exit_1(tmp_path: Path, damaged_root: Path, command: tuple[str, ...]) -> None:
    result = _bea(tmp_path, damaged_root, "-f", "main.bean", *command)
    message = " ".join(result.stderr.split())
    assert result.returncode == 1, result.stderr
    assert f"The managed Beancount engine at {damaged_root} is damaged" in message
    assert f"Remove {damaged_root} and rerun" in message
    assert "outcome is unknown" not in message and "Traceback" not in message
    assert (tmp_path / "main.bean").read_text() == LEDGER
