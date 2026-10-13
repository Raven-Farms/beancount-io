"""The optional-feature probe never imports from the working directory (w5/174).

`bea engine status`, the `price` passthroughs and `ingest` ask the engine
interpreter whether a feature's package is importable. The probe ran with the
working directory first on the module path, so a `beanprice.py` beside the
ledger was executed and an innocent `beanprice/` folder made the feature look
installed.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("beanprice") is not None,
    reason="beanprice is installed in the test interpreter, so the feature is really present",
)


def _bea(tmp_path: Path, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_ENGINE_PYTHON=sys.executable,
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-P", "-m", "cli.main", *args],
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _beanprice_status(tmp_path: Path, cwd: Path) -> dict[str, object]:
    result = _bea(tmp_path, cwd, "--json", "engine", "status")
    assert result.returncode == 0, result.stderr
    feature = json.loads(result.stdout)["data"]["features"]["beanprice"]
    assert isinstance(feature, dict)
    return feature


@pytest.fixture
def clean(tmp_path: Path) -> Path:
    directory = tmp_path / "clean"
    directory.mkdir()
    return directory


@pytest.fixture
def with_file(tmp_path: Path) -> Path:
    directory = tmp_path / "untrusted"
    directory.mkdir()
    marker = tmp_path / "marker"
    (directory / "beanprice.py").write_text(f"open({str(marker)!r}, 'a').write('ran\\n')\n")
    return directory


@pytest.fixture
def with_folder(tmp_path: Path) -> Path:
    directory = tmp_path / "folder"
    (directory / "beanprice").mkdir(parents=True)
    return directory


def test_a_module_file_in_the_working_directory_is_not_executed(tmp_path: Path, clean: Path, with_file: Path) -> None:
    control = _beanprice_status(tmp_path, clean)
    assert control["present"] is False

    assert _beanprice_status(tmp_path, with_file) == control
    assert not (tmp_path / "marker").exists()


def test_an_empty_folder_in_the_working_directory_is_not_a_feature(
    tmp_path: Path, clean: Path, with_folder: Path
) -> None:
    control = _beanprice_status(tmp_path, clean)
    assert control["present"] is False

    assert _beanprice_status(tmp_path, with_folder) == control


@pytest.mark.parametrize("directory", ["with_file", "with_folder"])
def test_price_refuses_the_same_way_from_either_directory(
    tmp_path: Path, clean: Path, directory: str, request: pytest.FixtureRequest
) -> None:
    control = _bea(tmp_path, clean, "price", "list")
    assert control.returncode == 2
    assert "Engine feature 'beanprice' is not available" in control.stderr

    shadowed = _bea(tmp_path, request.getfixturevalue(directory), "price", "list")
    assert (shadowed.returncode, shadowed.stderr) == (control.returncode, control.stderr)
    assert not (tmp_path / "marker").exists()
