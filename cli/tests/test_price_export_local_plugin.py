"""`price export` carries a plugin module that lives beside the ledger (w5/094).

With `option "insert_pythonpath"`, `plugin "myplug"` may name a module next to
the root. The export copied the ledger and not the module, reported success,
and produced a snapshot stock `bean-check` could not load.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

PLUGIN = '__plugins__ = ["noop"]\n\n\ndef noop(entries, options_map, config=None):\n    return entries, []\n'
LEDGER = """\
option "operating_currency" "USD"
option "insert_pythonpath" "TRUE"
plugin "{plugin}"

2026-01-01 open Assets:Checking USD
2026-01-01 open Equity:Opening
"""
PLAIN = 'option "operating_currency" "USD"\n\n2026-01-01 open Assets:Checking USD\n2026-01-01 open Equity:Opening\n'


def _stock_check(target: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "beancount.scripts.check", str(target)],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=target.parent.parent.parent,
    )


def _export(books: Path, *args: str) -> Any:
    return runner.invoke(app, ["--offline", "--file", str(books / "main.bean"), "price", "export", *args])


@pytest.fixture
def books(tmp_path: Path, bea_config_dir: Path) -> Path:
    directory = tmp_path / "work" / "books"
    directory.mkdir(parents=True)
    return directory


@pytest.mark.parametrize("shape", ["module", "package", "submodule"])
def test_a_plugin_beside_the_ledger_travels_with_the_export(books: Path, shape: str) -> None:
    if shape == "module":
        (books / "myplug.py").write_text(PLUGIN)
        plugin, expected = "myplug", ["myplug.py"]
    else:
        (books / "myplug").mkdir()
        (books / "myplug" / "__init__.py").write_text(PLUGIN if shape == "package" else "")
        (books / "myplug" / "inner.py").write_text(PLUGIN)
        (books / "myplug" / "__pycache__").mkdir()
        (books / "myplug" / "__pycache__" / "inner.cpython-312.pyc").write_bytes(b"\\0")
        plugin = "myplug" if shape == "package" else "myplug.inner"
        expected = ["myplug/__init__.py", "myplug/inner.py"]
    (books / "main.bean").write_text(LEDGER.format(plugin=plugin))

    result = _export(books)

    assert result.exit_code == 0, result.output
    exported = books / "main-export"
    assert sorted(str(path.relative_to(exported)) for path in exported.rglob("*") if path.is_file()) == sorted(
        ["main.bean", *expected]
    )
    assert f"Exported {len(expected) + 1} files" in result.output
    checked = _stock_check(exported / "main.bean")
    assert checked.returncode == 0, checked.stderr


def test_an_existing_module_at_the_destination_is_not_overwritten_without_force(books: Path) -> None:
    (books / "myplug.py").write_text(PLUGIN)
    (books / "main.bean").write_text(LEDGER.format(plugin="myplug"))
    out = books.parent / "out"
    out.mkdir()
    (out / "myplug.py").write_text("# someone else's\\n")

    refused = _export(books, "--output", str(out))

    assert refused.exit_code == 2, refused.output
    assert (out / "myplug.py").read_text() == "# someone else's\\n"
    assert not (out / "main.bean").exists()


def test_a_plugin_installed_elsewhere_is_left_alone(books: Path) -> None:
    (books / "main.bean").write_text(LEDGER.format(plugin="beancount.plugins.auto_accounts"))

    result = _export(books)

    assert result.exit_code == 0, result.output
    assert [path.name for path in (books / "main-export").rglob("*")] == ["main.bean"]


def test_a_plugin_free_ledger_exports_as_before(books: Path) -> None:
    (books / "main.bean").write_text(PLAIN)

    result = _export(books)

    assert result.exit_code == 0, result.output
    assert (books / "main-export" / "main.bean").read_text() == PLAIN
    assert _stock_check(books / "main-export" / "main.bean").returncode == 0
