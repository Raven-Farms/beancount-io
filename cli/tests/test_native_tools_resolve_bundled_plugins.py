"""Upstream executables resolve the bundled `fava.plugins.*` the helper resolves (w5/084).

`bean-check` and `bean-doctor` were started without the helper's module
search path, so on a managed engine a ledger using `fava.plugins.forecast`
failed plain `bea check` with `No module named 'fava'` while `--json check`,
reports and queries loaded it.
"""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.engine import launch, paths
from cli.main import app

runner = CliRunner()

LEDGER = """\
option "operating_currency" "USD"
plugin "{plugin}"

2024-01-01 open Assets:Checking USD
2024-01-01 open Equity:Opening
2024-01-01 open Expenses:Rent

2024-01-01 * "Opening balance"
  Assets:Checking  10000.00 USD
  Equity:Opening

2024-01-15 # "Rent [MONTHLY REPEAT 3 TIMES]"
  Expenses:Rent  1000.00 USD
  Assets:Checking
"""

# A stand-in executable whose interpreter sees no site directory, as a managed
# engine's does not see this checkout: `fava` is importable only through the
# search path the launcher provides.
PROBE = """#!/bin/sh
exec "{python}" -S -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('fava') else 7)"
"""


@pytest.fixture
def isolated_native(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    probe = tmp_path / "bean-check"
    probe.write_text(PROBE.format(python=sys.executable))
    probe.chmod(probe.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setattr(launch, "native_command", lambda name: probe)
    return probe


@pytest.mark.skipif(sys.platform == "win32", reason="the stand-in executable is a shell script")
@pytest.mark.parametrize("inherited", [None, "/somewhere/else"], ids=["no-pythonpath", "with-pythonpath"])
def test_a_native_tool_can_import_the_bundled_fava_package(
    isolated_native: Path, monkeypatch: pytest.MonkeyPatch, inherited: str | None
) -> None:
    if inherited is None:
        monkeypatch.delenv("PYTHONPATH", raising=False)
    else:
        monkeypatch.setenv("PYTHONPATH", inherited)

    assert launch.run_native("bean-check", []) == 0
    assert launch.capture_native("bean-check", []).returncode == 0


def test_the_native_search_path_keeps_an_inherited_one_first(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYTHONPATH", "/somewhere/else")

    entries = launch._native_env()["PYTHONPATH"].split(os.pathsep)

    assert entries == ["/somewhere/else", str(paths.helper_source_root())]


def test_the_native_environment_carries_no_managed_price_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BEA_MANAGED_PRICE_TOKEN", raising=False)

    assert "BEA_MANAGED_PRICE_TOKEN" not in launch._native_env()


@pytest.mark.parametrize("plugin", ["fava.plugins.forecast", "fava.plugins.link_documents"])
def test_plain_and_json_check_agree_on_a_bundled_plugin(tmp_path: Path, bea_config_dir: Path, plugin: str) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER.format(plugin=plugin))

    plain = runner.invoke(app, ["--file", str(ledger), "check"])
    as_json = runner.invoke(app, ["--json", "--file", str(ledger), "check"])

    assert plain.exit_code == 0, plain.output
    assert "No module named" not in plain.output
    assert as_json.exit_code == 0, as_json.output
    assert json.loads(as_json.stdout)["data"]["valid"] is True


def test_doctor_loads_a_ledger_that_uses_a_bundled_plugin(tmp_path: Path, bea_config_dir: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER.format(plugin="fava.plugins.forecast"))

    for operation in ("print-options", "missing-open"):
        result = runner.invoke(app, ["doctor", operation, str(ledger)])
        assert result.exit_code == 0, result.output
        assert "No module named" not in result.output


def test_a_plugin_that_does_not_exist_still_fails_in_both_modes(tmp_path: Path, bea_config_dir: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER.format(plugin="no.such.plugin"))

    plain = runner.invoke(app, ["--file", str(ledger), "check"])
    as_json = runner.invoke(app, ["--json", "--file", str(ledger), "check"])

    assert plain.exit_code == 1, plain.output
    assert as_json.exit_code == 1, as_json.output
