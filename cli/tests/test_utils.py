from __future__ import annotations

from datetime import date

import pytest
import typer

from cli.utils import parse_date, parse_opt_date


def test_parse_date_parses_iso_date() -> None:
    assert parse_date("2026-07-27") == date(2026, 7, 27)


def test_parse_date_rejects_invalid_with_bad_parameter() -> None:
    with pytest.raises(typer.BadParameter) as exc:
        parse_date("not-a-date")
    assert exc.value.message == "Invalid date 'not-a-date'. Use YYYY-MM-DD format."


@pytest.mark.parametrize("value", ["2027-02-29", "2026-04-31", "2026-13-01"])
def test_a_well_formed_day_that_does_not_exist_is_named_as_such(value: str) -> None:
    # It is already YYYY-MM-DD; the format hint sent it back unchanged (w5/330).
    with pytest.raises(typer.BadParameter) as exc:
        parse_date(value)
    assert exc.value.message.startswith(f"Invalid date '{value}': not a calendar date (")
    assert "Use YYYY-MM-DD format" not in exc.value.message


def test_parse_opt_date_passes_through_none() -> None:
    assert parse_opt_date(None) is None


def test_parse_opt_date_parses_a_value() -> None:
    assert parse_opt_date("2026-01-02") == date(2026, 1, 2)
