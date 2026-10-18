"""Follow-ups to w5/480 and w5/475 (w5/633).

An allowlist whose every entry is ignored read "managed price includes are
disabled", the words for an empty variable, and never named the entry. An
`option` on line 1 of a file that opens with a byte-order mark lost its
` at FILE:1` location.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
MANAGED = '2020-01-01 open Assets:BTC BTC\ninclude "https://beancount.io/prices/BTC-USD"\n'


@pytest.mark.parametrize(
    ("origins", "said"),
    [
        ("beancount.io", "MANAGED_PRICE_ORIGINS entry 'beancount.io' is not an http(s) origin and was ignored"),
        ("htps://beancount.io", "MANAGED_PRICE_ORIGINS entry 'htps://beancount.io' is not an http(s) origin"),
        (
            "beancount.io, ftp://x",
            "MANAGED_PRICE_ORIGINS entries 'beancount.io', 'ftp://x' are not http(s) origins and were ignored",
        ),
        ("", "managed price includes are disabled"),
    ],
    ids=["bare-host", "typo-scheme", "two-entries", "empty"],
)
def test_an_all_ignored_allowlist_names_its_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, origins: str, said: str
) -> None:
    monkeypatch.setenv("MANAGED_PRICE_ORIGINS", origins)
    ledger = tmp_path / "main.bean"
    ledger.write_text(MANAGED)

    result = runner.invoke(app, ["--offline", "-f", str(ledger), "check"])

    assert result.exit_code == 1, result.output
    output = " ".join(result.output.split())
    assert said in output
    if origins:
        assert "no origins remain" in output and "disabled" not in output


def test_one_valid_entry_keeps_the_allowlist_wording(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MANAGED_PRICE_ORIGINS", "beancount.io, https://example.com")
    ledger = tmp_path / "main.bean"
    ledger.write_text(MANAGED)

    result = runner.invoke(app, ["--offline", "-f", str(ledger), "check"])

    assert "origin https://beancount.io is not allowlisted" in " ".join(result.output.split())


@pytest.mark.parametrize("mark", [b"\xef\xbb\xbf", b""], ids=["bom", "plain"])
def test_an_option_on_a_marked_first_line_keeps_its_location(tmp_path: Path, mark: bytes) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_bytes(mark + b'option "operating_currency" "usd"\n2020-01-01 open Assets:Cash USD\n')

    result = runner.invoke(app, ["-f", str(ledger), "report", "balance-sheet"])

    assert result.exit_code != 0
    assert f'option "operating_currency" "usd" at {ledger}:1 is not a Beancount currency' in " ".join(
        result.output.split()
    )
