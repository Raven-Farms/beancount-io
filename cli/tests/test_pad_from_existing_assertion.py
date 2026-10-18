"""A successful pad validation must not bypass balance idempotency (w5/659)."""

import json
from pathlib import Path

import pytest
from click.testing import Result
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
OPENS = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n2026-01-01 open Equity:Opening USD\n'


def _add(root: Path, amount: str, json_output: bool, *extra: str) -> Result:
    return runner.invoke(
        app,
        [
            *(["--json"] if json_output else []),
            "--file",
            str(root),
            "add",
            "balance",
            "--date",
            "2026-01-25",
            "-a",
            "Assets:Cash",
            "--amount",
            amount,
            "--pad-from",
            "Equity:Opening",
            *extra,
        ],
    )


@pytest.mark.parametrize("amount", ["7 ~ 0.5 USD", "7 USD", "7.000 USD"])
@pytest.mark.parametrize("allow_errors", [False, True])
@pytest.mark.parametrize("json_output", [False, True])
def test_a_pad_that_would_validate_still_requires_force_for_a_conflict(
    tmp_path: Path, amount: str, allow_errors: bool, json_output: bool
) -> None:
    root = tmp_path / "main.bean"
    original = OPENS + "2026-01-25 balance Assets:Cash 7.00 USD\n"
    root.write_text(original)

    result = _add(root, amount, json_output, *(["--allow-errors"] if allow_errors else []))

    assert result.exit_code == 4, result.output
    diagnostic = json.dumps(json.loads(result.stderr)["error"]) if json_output else result.output
    text = " ".join(diagnostic.split())
    assert "already has a 2026-01-25 balance of 7.00 USD" in text
    assert f"refusing {amount}. Pass --force" in text
    assert root.read_text() == original
    assert not list(tmp_path.glob(".bea-*"))


@pytest.mark.parametrize("amount", ["0.00 USD", "7.00 USD"])
@pytest.mark.parametrize("split", [False, True])
@pytest.mark.parametrize("json_output", [False, True])
def test_an_identical_assertion_is_reported_without_a_second_assertion_or_pad(
    tmp_path: Path, amount: str, split: bool, json_output: bool
) -> None:
    root = tmp_path / "main.bean"
    existing = tmp_path / "assertions.bean" if split else root
    if split:
        root.write_text(OPENS + 'include "assertions.bean"\n')
        existing.write_text(f"2026-01-25 balance Assets:Cash {amount}\n")
    else:
        root.write_text(OPENS + f"2026-01-25 balance Assets:Cash {amount}\n")
    before = {path: path.read_bytes() for path in tmp_path.glob("*.bean")}

    result = _add(root, amount, json_output)

    assert result.exit_code == 0, result.output
    line = 1 if split else 4
    if json_output:
        data = json.loads(result.stdout)["data"]
        assert data["written"] == 0 and data["duplicate"] is True
        assert data["pad"] is None
        assert data["source"] == {"filename": str(existing), "lineno": line}
        warnings = " ".join(data["warnings"])
    else:
        text = " ".join(result.output.split())
        assert f"Balance already recorded at {existing}:{line}; nothing was written." in text
        assert "Added 1 pad" not in text
        warnings = text
    # A failed existing assertion stays visible; a duplicate does not claim
    # that --pad-from repaired the books.
    if amount == "7.00 USD":
        assert "Balance failed" in warnings
        assert "Book balance already matches" not in warnings
    else:
        assert "Book balance already matches 0.00 USD" in warnings
        assert "omitted the pad from --pad-from" in warnings
    assert {path: path.read_bytes() for path in tmp_path.glob("*.bean")} == before


@pytest.mark.parametrize("json_output", [False, True])
def test_force_can_record_a_different_tolerance_when_both_assertions_validate(
    tmp_path: Path, json_output: bool
) -> None:
    root = tmp_path / "main.bean"
    root.write_text(OPENS + "2026-01-25 balance Assets:Cash 7.00 USD\n")

    result = _add(root, "7 ~ 0.5 USD", json_output, "--force")

    assert result.exit_code == 0, result.output
    assert root.read_text().count(" balance Assets:Cash ") == 2
    assert root.read_text().count(" pad Assets:Cash ") == 1
    if json_output:
        assert json.loads(result.stdout)["data"]["written"] == 2
    assert runner.invoke(app, ["--file", str(root), "check"]).exit_code == 0
