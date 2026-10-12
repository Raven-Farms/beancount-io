"""`format --check` / `-i` see whole ledgers: includes, parse errors, missing targets (w3/273, w3/332, w3/370)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bea_engine.ledger.text import syntax_errors
from cli.main import app

runner = CliRunner()

MISALIGNED_CHILD = '2020-02-01 * "seed"\n  Assets:Cash  -1 USD\n  Expenses:Food  1 USD\n'


def _split_ledger(directory: Path) -> Path:
    root = directory / "main.bean"
    root.write_text('include "child.bean"\n2020-01-01 open Assets:Cash USD\n')
    (directory / "child.bean").write_text(MISALIGNED_CHILD)
    return root


def test_check_fails_on_missing_include_and_names_it(tmp_path: Path) -> None:
    root = tmp_path / "main.bean"
    root.write_text('include "missing.bean"\n2020-01-01 open Assets:Cash USD\n')
    result = runner.invoke(app, ["format", str(root), "--check"])
    assert result.exit_code == 1, result.output
    assert 'missing include: "missing.bean"' in result.output
    assert str(root) in result.output
    as_json = runner.invoke(app, ["--json", "format", str(root), "--check"])
    assert as_json.exit_code == 1, as_json.output
    error = json.loads(as_json.stderr)["error"]
    assert error["result"]["missing"] == [{"include": "missing.bean", "from": str(root)}]


MANAGED = 'include "https://beancount.io/prices/BTC-USD"\n'


@pytest.mark.parametrize("shape", ["named-file", "directory", "child"])
def test_a_managed_price_include_is_not_a_missing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, shape: str
) -> None:
    """The formatter globbed the feed URL, so the gate failed on every such ledger (w5/069)."""
    monkeypatch.setenv("MANAGED_PRICE_OFFLINE", "1")
    books = tmp_path / "books"
    books.mkdir()
    root = books / "main.bean"
    if shape == "child":
        root.write_text('include "prices.bean"\n2020-01-01 open Assets:Cash USD\n')
        (books / "prices.bean").write_text(MANAGED)
    else:
        root.write_text(f'option "operating_currency" "USD"\n{MANAGED}\n2020-01-01 open Assets:Cash USD\n')
    target = str(books if shape == "directory" else root)
    before = {path: path.read_bytes() for path in books.iterdir()}

    for mode in (["--check"], ["--dry-run"], ["-i"]):
        result = runner.invoke(app, ["format", target, *mode])
        assert result.exit_code == 0, result.output
        assert "missing include" not in result.output
    as_json = runner.invoke(app, ["--json", "format", target, "--check"])
    assert as_json.exit_code == 0, as_json.output
    assert json.loads(as_json.stdout)["data"]["missing"] == []
    assert {path: path.read_bytes() for path in books.iterdir()} == before


def test_a_misaligned_ledger_with_a_managed_include_is_formatted_in_place(tmp_path: Path) -> None:
    root = tmp_path / "main.bean"
    root.write_text(MANAGED + MISALIGNED_CHILD)

    result = runner.invoke(app, ["format", "-i", str(root)])

    assert result.exit_code == 0, result.output
    assert root.read_text().startswith(MANAGED)
    assert root.read_text() != MANAGED + MISALIGNED_CHILD
    assert runner.invoke(app, ["format", str(root), "--check"]).exit_code == 0


def test_a_missing_local_include_beside_a_managed_one_is_still_named_alone(tmp_path: Path) -> None:
    root = tmp_path / "main.bean"
    root.write_text(MANAGED + 'include "missing.bean"\n2020-01-01 open Assets:Cash USD\n')

    result = runner.invoke(app, ["--json", "format", str(root), "--check"])

    assert result.exit_code == 1, result.output
    assert json.loads(result.stderr)["error"]["result"]["missing"] == [{"include": "missing.bean", "from": str(root)}]


def test_check_fails_on_unparseable_files_and_leaves_them_untouched(tmp_path: Path) -> None:
    garbage = tmp_path / "garbage.bean"
    garbage.write_text("not beancount\n")
    half = tmp_path / "half.bean"
    half.write_text("2020-01-01 open\n")
    before = (garbage.read_bytes(), half.read_bytes())
    for target in (garbage, half):
        result = runner.invoke(app, ["format", str(target), "--check"])
        assert result.exit_code == 1, result.output
        assert "cannot parse" in result.output
        assert str(target) in result.output
    assert (garbage.read_bytes(), half.read_bytes()) == before
    as_json = runner.invoke(app, ["--json", "format", str(garbage), "--check"])
    assert as_json.exit_code == 1, as_json.output
    failed = json.loads(as_json.stderr)["error"]["result"]["failed"]
    assert failed[0]["file"] == str(garbage)
    assert any("Invalid token" in error for error in failed[0]["errors"])


def test_check_and_in_place_honor_the_include_closure(tmp_path: Path) -> None:
    root = _split_ledger(tmp_path)
    child = tmp_path / "child.bean"
    check = runner.invoke(app, ["format", str(root), "--check"])
    assert check.exit_code == 1, check.output
    assert str(child) in check.output
    fixed = runner.invoke(app, ["format", str(root), "-i"])
    assert fixed.exit_code == 0, fixed.output
    assert child.read_text() != MISALIGNED_CHILD
    green = runner.invoke(app, ["format", str(root), "--check"])
    assert green.exit_code == 0, green.output
    assert f"checked: {child}" in green.output
    assert f"checked: {root}" in green.output
    assert "All 2 file(s) are formatted." in green.output


def test_in_place_skips_garbage_and_formats_the_rest(tmp_path: Path) -> None:
    root = _split_ledger(tmp_path)
    garbage = tmp_path / "garbage.bean"
    garbage.write_text("not beancount\n")
    before = garbage.read_bytes()
    result = runner.invoke(app, ["format", str(tmp_path), "-i"])
    assert result.exit_code == 1, result.output
    assert (tmp_path / "child.bean").read_text() != MISALIGNED_CHILD
    assert garbage.read_bytes() == before
    assert "cannot parse" in result.stderr
    assert str(root) in result.stderr or str(tmp_path / "child.bean") in result.stderr


def test_stdout_mode_stays_a_single_file_filter(tmp_path: Path) -> None:
    root = _split_ledger(tmp_path)
    result = runner.invoke(app, ["format", str(root)])
    assert result.exit_code == 0, result.output
    assert "Assets:Cash" in result.stdout
    assert "Expenses:Food" not in result.stdout


def test_semantic_errors_do_not_fail_check(tmp_path: Path) -> None:
    """`--check` is alignment plus parseability; `check` owns semantics."""
    root = tmp_path / "main.bean"
    root.write_text(
        "2020-01-01 open Assets:Cash USD\n"
        "2020-01-01 open Equity:Opening-Balances\n"
        "2020-01-05 balance Assets:Cash 999 USD\n"
    )
    check = runner.invoke(app, ["--file", str(root), "check"])
    assert check.exit_code == 1, check.output
    fixed = runner.invoke(app, ["format", str(root), "-i"])
    assert fixed.exit_code == 0, fixed.output
    result = runner.invoke(app, ["format", str(root), "--check"])
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize(
    ("name", "content", "expect_errors"),
    [
        ("child.bean", '2020-02-01 * "x"\n  Assets:Cash -1 USD\n  Expenses:Food 1 USD\n', False),
        ("garbage.bean", "not beancount\n", True),
        ("half.bean", "2020-01-01 open\n", True),
    ],
)
def test_syntax_errors_oracle(tmp_path: Path, name: str, content: str, expect_errors: bool) -> None:
    target = tmp_path / name
    target.write_text(content)
    assert (syntax_errors(target) != []) is expect_errors


def test_syntax_errors_names_unreadable_files(tmp_path: Path) -> None:
    missing = tmp_path / "gone.bean"
    assert syntax_errors(missing) == [f"{missing}: cannot read file (No such file or directory)."]
