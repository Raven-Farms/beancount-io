"""The query shell keeps Beanquery's history file, which follows HOME and not BEA_CONFIG_DIR (w5/392).

USAGE said only that `.exit` "saves its history", while BEA_CONFIG_DIR is
documented as the home of per-user state; an isolated setup still wrote the
history under the real home. The path is bean-query's, shared on purpose, and
is now documented where a user looks for either.
"""

from __future__ import annotations

from pathlib import Path

from tests.query_terminal import ROOT, QueryTerminal

PROMPT = "beanquery> "
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Cash USD
2026-01-01 open Expenses:Food USD
2026-01-05 * "Cafe" "Coffee"
  Expenses:Food  4.00 USD
  Assets:Cash
"""
HISTORY = ".config/beanquery/history"


def test_history_lands_under_home_not_the_config_dir(tmp_path: Path) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")
    home = tmp_path / "home"
    home.mkdir()
    # Without the harness's startup directory the history constant is upstream's own.
    env = {"HOME": str(home), "PYTHONPATH": str(ROOT / "src")}
    with QueryTerminal(tmp_path, ["-f", str(ledger), "query"], env=env) as terminal:
        terminal.read(PROMPT)
        terminal.send("SELECT sum(position) AS total WHERE account ~ 'Food'")
        terminal.read(PROMPT)
        status = terminal.finish()
        screen = terminal.screen

    assert status == 0, screen
    assert "4.00 USD" in screen, screen
    history = home / HISTORY
    assert history.is_file(), screen
    assert "account ~ 'Food'" in history.read_text(encoding="utf-8", errors="replace").replace("\\040", " ")
    assert not any("history" in path.name for path in (tmp_path / "config").rglob("*"))


def test_usage_names_the_path_in_the_shell_section_and_the_environment_table() -> None:
    usage = (ROOT / "docs" / "USAGE.md").read_text(encoding="utf-8")
    shell = usage.split("`.exit` (or `Ctrl-D`) ends the session", 1)[1].split("\n\n", 1)[0]
    assert "~/.config/beanquery/history" in shell
    row = next(line for line in usage.splitlines() if line.startswith("| `BEA_CONFIG_DIR` |"))
    assert "~/.config/beanquery/" in row
