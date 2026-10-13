"""An ImportError raised by an importer configuration is a missing engine
package only when a module cannot be found (w5/142)."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
DEPENDENCY = "Importer dependency is unavailable"


@pytest.fixture
def book(tmp_path: Path) -> Path:
    result = runner.invoke(app, ["--json", "init", str(tmp_path), "--currency", "USD", "--date", "2026-08-01"])
    assert result.exit_code == 0, result.output
    return tmp_path / "main.bean"


def _import(book: Path, body: str, *leading: str):
    configs = book.parent / "c"
    configs.mkdir()
    (configs / "helper.py").write_text('ACCOUNT = "Assets:Checking"\n')
    config = configs / "config.py"
    config.write_text(body)
    source = book.parent / "x.txt"
    source.write_text("one line\n")
    return runner.invoke(app, [*leading, "--file", str(book), "import", str(source), "--config", str(config)])


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        ("from helper import ACCOUNTS\nCONFIG = []\n", "cannot import name 'ACCOUNTS' from 'helper'"),
        ("from . import helper\nCONFIG = []\n", "attempted relative import with no known parent package"),
        ("import helper.rules\nCONFIG = []\n", "'helper' is not a package"),
    ],
)
def test_a_mistaken_sibling_import_is_an_importer_failure(book: Path, body: str, reason: str) -> None:
    result = _import(book, body)

    assert result.exit_code == 1, result.output
    assert "Importer failed (" in result.stderr and "Error)" in result.stderr
    assert reason in result.stderr
    assert "runs as a script" in result.stderr
    assert DEPENDENCY not in result.stderr
    assert "installed" not in result.stderr


def test_a_mistaken_sibling_import_is_an_importer_failure_in_json(book: Path) -> None:
    result = _import(book, "from helper import ACCOUNTS\nCONFIG = []\n", "--json")

    assert result.exit_code == 1, result.output
    combined = result.stdout + result.stderr
    assert "Importer failed (ImportError): cannot import name 'ACCOUNTS'" in combined
    assert DEPENDENCY not in combined


def test_a_sibling_import_that_resolves_still_loads(book: Path) -> None:
    result = _import(book, "import helper\nCONFIG = []\n")

    assert result.exit_code == 2, result.output
    assert "No configured importer recognizes x.txt" in result.stderr


def test_an_absent_package_keeps_the_dependency_message(book: Path) -> None:
    result = _import(book, "import definitely_not_installed_module_xyz\nCONFIG = []\n")

    assert result.exit_code == 2, result.output
    assert DEPENDENCY in result.stderr
    assert "managed engine" in result.stderr
