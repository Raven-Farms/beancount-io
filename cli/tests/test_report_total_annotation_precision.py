"""Total-price division noise never becomes a report's money precision (w5/668)."""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from click.testing import Result
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
REPORTS = [
    ("report", "overview"),
    ("report", "income-statement"),
    ("report", "balance-sheet"),
    ("report", "trial-balance"),
    ("balance",),
]


def _books(
    tmp_path: Path, currency: str, total: str, annotation: str, *, flows: bool = True, quantity: str = "3"
) -> Path:
    root = tmp_path / "main.bean"
    quoted = f"@@ {total} {currency}" if annotation == "price" else f"{{{{{total} {currency}}}}}"
    root.write_text(
        f'option "operating_currency" "{currency}"\n'
        f"2026-01-01 open Assets:Cash {currency}\n"
        "2026-01-01 open Assets:Broker\n"
        f"2026-01-01 open Expenses:Food {currency}\n"
        "2026-01-01 open Equity:Opening\n"
        + (
            '2026-01-02 * "Fund"\n'
            f"  Assets:Cash 100000 {currency}\n"
            "  Equity:Opening\n"
            '2026-01-03 * "Lunch"\n'
            f"  Expenses:Food 1200 {currency}\n"
            "  Assets:Cash\n"
            if flows
            else ""
        )
        + '2026-01-04 * "Buy"\n'
        + f"  Assets:Broker {quantity} HOOL {quoted}\n"
        + "  Assets:Cash\n"
    )
    return root


def _run(root: Path, *args: str, json_mode: bool = False) -> Result:
    result = runner.invoke(app, [*(["--json"] if json_mode else []), "--file", str(root), *args])
    assert result.exit_code == 0, result.output
    return result


def _data(root: Path, *args: str) -> dict[str, Any]:
    return dict(json.loads(_run(root, *args, json_mode=True).stdout)["data"])


@pytest.mark.parametrize("annotation", ["price", "cost"])
@pytest.mark.parametrize("command", REPORTS, ids=lambda args: "-".join(args))
def test_every_human_report_keeps_whole_yen_money(tmp_path: Path, annotation: str, command: tuple[str, ...]) -> None:
    root = _books(tmp_path, "JPY", "1000", annotation)
    before = root.read_bytes()

    result = _run(root, *command, "--conversion", "units")

    assert "1,200 JPY" in result.output
    assert ".000" not in result.output
    if command != ("report", "income-statement"):
        assert "97,800 JPY" in result.output
    assert root.read_bytes() == before


@pytest.mark.parametrize("annotation", ["price", "cost"])
def test_total_annotations_also_keep_whole_dollar_balances(tmp_path: Path, annotation: str) -> None:
    root = _books(tmp_path, "USD", "100", annotation)

    result = _run(root, "balance", "--conversion", "units")

    assert "1,200 USD" in result.output
    assert "98,700 USD" in result.output
    assert ".000" not in result.output


@pytest.mark.parametrize("currency,total", [("JPY", "1000"), ("USD", "100")])
@pytest.mark.parametrize("annotation", ["price", "cost"])
def test_json_caps_display_precision_without_rounding_actual_values(
    tmp_path: Path, currency: str, total: str, annotation: str
) -> None:
    # No other cash postings absorb the division residue before serialization.
    root = _books(tmp_path, currency, total, annotation, flows=False)
    before = root.read_bytes()

    data = _data(root, "report", "balance-sheet", "--conversion", "units")

    exact = -(Decimal(total) / Decimal(3) * Decimal(3))
    # Display precision is private rendering metadata; public JSON stays exact.
    assert "display_precision" not in data
    assert data["net_worth"][currency] == str(exact)
    assert exact != -Decimal(total)
    assert data["net_worth"]["HOOL"] == "3"
    assert root.read_bytes() == before


@pytest.mark.parametrize("quantity,expected", [("3", "968.5"), ("1.5", "984.25")])
def test_real_fractional_inferred_products_keep_their_precision(tmp_path: Path, quantity: str, expected: str) -> None:
    root = tmp_path / "main.bean"
    root.write_text(
        'option "operating_currency" "USD"\n'
        "2026-01-01 open Assets:Cash USD\n"
        "2026-01-01 open Assets:Broker\n"
        "2026-01-01 open Equity:Opening\n"
        '2026-01-02 * "Fund"\n'
        "  Assets:Cash 1000 USD\n"
        "  Equity:Opening\n"
        '2026-01-03 * "Buy"\n'
        f"  Assets:Broker {quantity} HOOL @ 10.5 USD\n"
        "  Assets:Cash\n"
    )

    result = _run(root, "balance", "Cash", "--conversion", "units")
    data = _data(root, "report", "balance-sheet", "--conversion", "units")

    assert f"{expected} USD" in result.output
    assert Decimal(data["net_worth"]["USD"]) == Decimal(expected)


def test_a_written_fractional_amount_still_sets_the_money_precision(tmp_path: Path) -> None:
    root = _books(tmp_path, "JPY", "1000", "price")
    with root.open("a") as stream:
        stream.write('2026-01-05 * "Snack"\n  Expenses:Food 0.25 JPY\n  Assets:Cash\n')

    result = _run(root, "balance", "--conversion", "units")
    data = _data(root, "report", "balance-sheet", "--conversion", "units")

    assert "1,200.25 JPY" in result.output
    assert "97,799.75 JPY" in result.output
    assert Decimal(data["net_worth"]["JPY"]) == Decimal("97799.75")


@pytest.mark.parametrize("currency,total", [("JPY", "1000"), ("USD", "100")])
def test_explicit_display_precision_still_wins(tmp_path: Path, currency: str, total: str) -> None:
    root = _books(tmp_path, currency, total, "price")
    root.write_text(f'option "display_precision" "{currency}:0.001"\n' + root.read_text())

    result = _run(root, "report", "income-statement", "--conversion", "units")
    data = _data(root, "report", "income-statement", "--conversion", "units")

    assert f"1,200.000 {currency}" in result.output
    assert Decimal(data["net_profit"][currency]) == Decimal(-1200)


@pytest.mark.parametrize("annotation", ["price", "cost"])
def test_fractional_units_do_not_widen_the_whole_total_currency(tmp_path: Path, annotation: str) -> None:
    root = _books(tmp_path, "JPY", "1000", annotation, quantity="1.5")

    result = _run(root, "balance", "--conversion", "units")
    data = _data(root, "report", "balance-sheet", "--conversion", "units")

    assert "1.5 HOOL" in result.output
    assert "1,200 JPY" in result.output
    assert "97,800 JPY" in result.output
    assert ".000" not in result.output
    assert data["net_worth"]["HOOL"] == "1.5"


def test_a_report_load_refreshes_written_precision_after_the_source_changes(tmp_path: Path) -> None:
    from bea_engine import report

    root = _books(tmp_path, "JPY", "1000", "price")
    first = report.answer(root, "balance-sheet", conversion="units")
    assert first["display_precision"]["JPY"] == 0

    root.write_text(root.read_text().replace("@@ 1000 JPY", "@ 10.5 JPY"))
    second = report.answer(root, "balance-sheet", conversion="units")

    assert second["display_precision"]["JPY"] == 1
    assert second["net_worth"]["JPY"] == Decimal("98768.5")
