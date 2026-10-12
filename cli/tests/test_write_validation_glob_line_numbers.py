"""Write validation keeps an includer's line numbering under a multi-file glob (w5/079).

A staged includer wrote a glob's N matches as N include lines, moving every
later line down N-1. The pre-write errors were read from the real files, so a
balance assertion already failing below the include was counted as newly
introduced and `--allow-errors` refused every write.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

MAIN = """\
option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Food
2026-01-01 open Equity:Opening
include "{include}"
2026-01-02 * "Open"
  Assets:Checking  100.00 USD
  Equity:Opening
2026-01-05 balance Assets:Checking  {asserted} USD
"""
ADD = ["add", "transaction", "x", "--date", "2026-03-01", "-p", "Expenses:Food 5 USD", "-p", "Assets:Checking"]


def _books(tmp_path: Path, matches: int, *, asserted: str = "999.00", include: str = "sub/*.bean") -> Path:
    (tmp_path / "sub").mkdir()
    for index, name in enumerate("abc"[:matches], start=1):
        (tmp_path / "sub" / f"{name}.bean").write_text(
            f'2026-02-0{index} * "{name}"\n  Expenses:Food  {index}.00 USD\n  Assets:Checking\n'
        )
    root = tmp_path / "main.bean"
    root.write_text(MAIN.format(include=include, asserted=asserted))
    return root


def _flat(output: str) -> str:
    return " ".join(output.split())


@pytest.mark.parametrize("matches", [1, 2, 3])
@pytest.mark.parametrize("into", [None, "sub/a.bean"], ids=["root", "into"])
def test_allow_errors_writes_over_an_error_below_a_glob_include(
    tmp_path: Path, bea_config_dir: Path, matches: int, into: str | None
) -> None:
    root = _books(tmp_path, matches)
    target = tmp_path / into if into else root
    extra = ["--into", into] if into else []

    result = runner.invoke(app, ["--file", str(root), *ADD, "--allow-errors", *extra])

    assert result.exit_code == 0, result.output
    flat = _flat(result.output)
    assert f"{root}:9: Balance failed for 'Assets:Checking'" in flat
    assert "would introduce" not in flat and "Proposed append" not in flat
    assert '2026-03-01 * "x"' in target.read_text()
    assert not list(tmp_path.rglob(".bea-*.tmp"))
    assert len(list((tmp_path / "sub").iterdir())) == matches


def test_a_literal_include_is_unchanged(tmp_path: Path, bea_config_dir: Path) -> None:
    root = _books(tmp_path, 1, include="sub/a.bean")

    result = runner.invoke(app, ["--file", str(root), *ADD, "--allow-errors"])

    assert result.exit_code == 0, result.output
    assert f"{root}:9: Balance failed" in _flat(result.output)


def test_a_closed_account_is_quoted_at_the_line_the_file_has(tmp_path: Path, bea_config_dir: Path) -> None:
    root = _books(tmp_path, 3, asserted="100.00")
    root.write_text(root.read_text() + "2026-02-15 close Expenses:Food\n")
    before = root.read_text()

    result = runner.invoke(app, ["--file", str(root), *ADD])

    assert result.exit_code == 1, result.output
    flat = _flat(result.output)
    assert f"Account opened 2026-01-01 at {root}:3." in flat
    assert f"Account closed 2026-02-15 at {root}:10." in flat
    assert root.read_text() == before


def test_a_write_that_really_breaks_the_assertion_is_still_refused_at_its_line(
    tmp_path: Path, bea_config_dir: Path
) -> None:
    root = _books(tmp_path, 3, asserted="100.00")
    before = root.read_text()
    breaking = [
        "add",
        "transaction",
        "x",
        "--date",
        "2026-01-03",
        "-p",
        "Equity:Opening 5 USD",
        "-p",
        "Assets:Checking",
    ]

    for flags in ([], ["--allow-errors"]):
        result = runner.invoke(app, ["--file", str(root), *breaking, *flags])
        assert result.exit_code == 1, result.output
        flat = _flat(result.output)
        assert f"{root}:9: Balance failed for 'Assets:Checking'" in flat
        assert "Proposed append" not in flat
        if not flags:
            assert f"existing assertion at {root}:9" in flat
    assert root.read_text() == before
