"""Ledger reads never leave plugin bytecode beside the books (w5/655)."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
PLUGIN = (
    "from datetime import date\n"
    "from beancount.core.data import Event, new_metadata\n"
    "__plugins__ = ['p']\n"
    "def p(entries, options):\n"
    "    return entries + [Event(new_metadata(__file__, 1), date(2026, 2, 1), 'plugin-check', 'Loaded')], []\n"
)


@pytest.mark.parametrize(
    "command", ["check", "json-check", "native-check", "list", "query", "balance", "report", "doctor"]
)
@pytest.mark.parametrize("linked_plugin", [False, True])
def test_read_leaves_no_local_plugin_bytecode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: str, linked_plugin: bool
) -> None:
    books = tmp_path / "books"
    books.mkdir()
    root = books / "main.bean"
    root.write_text('option "insert_pythonpath" "TRUE"\nplugin "myplug"\n2026-01-01 open Assets:Cash USD\n')
    external = tmp_path / "plugins"
    external.mkdir()
    plugin = books / "myplug.py"
    if linked_plugin:
        (external / "myplug.py").write_text(PLUGIN)
        plugin.symlink_to(external / "myplug.py")
    else:
        plugin.write_text(PLUGIN)
    monkeypatch.delenv("PYTHONDONTWRITEBYTECODE", raising=False)
    monkeypatch.delenv("PYTHONPYCACHEPREFIX", raising=False)
    args = {
        "check": ["check"],
        "json-check": ["--json", "check"],
        "native-check": ["check", "-v"],
        "list": ["list", "event"],
        "query": ["query", "SELECT account"],
        "balance": ["balance"],
        "report": ["report", "overview"],
        "doctor": ["doctor", "print-options", str(root)],
    }[command]

    result = runner.invoke(app, ["--file", str(root), *args])

    assert result.exit_code == 0, result.output
    assert not (books / "__pycache__").exists()
    assert not (external / "__pycache__").exists()
    assert plugin.read_text() == PLUGIN
    # Confirm plugins still execute when bytecode writing is disabled.
    events = runner.invoke(app, ["--file", str(root), "list", "event"])
    assert events.exit_code == 0, events.output
    assert "Loaded" in events.output
    assert not (books / "__pycache__").exists()
