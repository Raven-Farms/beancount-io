"""`price status` names a refused URL include instead of denying it exists (w5/861).

The load reported `include "https://…": managed price includes are disabled.`
and status then printed "No managed price includes in this ledger." (JSON:
`sources: []`), because a refused include is no source.
"""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
URL = "https://example.invalid/prices/BTC-USD"


def _status(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, text: str, *flags: str) -> tuple[int, str]:
    root = tmp_path / "main.bean"
    root.write_text(text)
    monkeypatch.setenv("MANAGED_PRICE_ORIGINS", "")
    before = root.read_bytes()
    result = runner.invoke(app, [*flags, "--offline", "--file", str(root), "price", "status"])
    assert root.read_bytes() == before
    return result.exit_code, result.stdout


def test_a_refused_include_is_listed_with_its_reason(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    code, stdout = _status(tmp_path, monkeypatch, f'include "{URL}"\n2026-01-01 open Assets:Checking USD\n')

    assert code == 0
    assert f"{URL}: managed price includes are disabled" in stdout
    assert "No managed price includes" not in stdout
    assert "No usable managed price sources." in stdout


def test_json_status_carries_the_refused_include(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    code, stdout = _status(tmp_path, monkeypatch, f'include "{URL}"\n2026-01-01 open Assets:Checking USD\n', "--json")

    assert code == 0
    data = json.loads(stdout)["data"]
    assert data["sources"] == []
    assert data["refused"] == [{"url": URL, "reason": "managed price includes are disabled"}]


@pytest.mark.parametrize("flags", [(), ("--json",)])
def test_a_ledger_without_url_includes_keeps_its_empty_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, flags: tuple[str, ...]
) -> None:
    code, stdout = _status(tmp_path, monkeypatch, "2026-01-01 open Assets:Checking USD\n", *flags)

    assert code == 0
    if flags:
        assert json.loads(stdout)["data"] == {"sources": [], "refused": []}
    else:
        assert stdout == "No managed price includes in this ledger.\n"
