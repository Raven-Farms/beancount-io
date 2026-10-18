"""Importer-shape refusals name the entry and its fix (w5/639).

A legacy importer beside a working one, or an importer listed as a class,
was refused with "Use the current Beangulp Importer interface", naming
neither. `extract()` returning one directive was "row 1 is a dict": `list()`
had taken the namedtuple's fields for rows.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()
IMPORTERS = textwrap.dedent("""
    import datetime
    from decimal import Decimal as D
    from beancount.core import amount, data

    def txn():
        legs = [data.Posting(a, amount.Amount(D(n), "USD"), None, None, None, None)
                for a, n in (("Assets:Checking", "-3.00"), ("Expenses:Food", "3.00"))]
        meta = data.new_metadata("bank.txt", 1)
        return data.Transaction(meta, datetime.date(2026, 2, 1), "*", None, "r1", data.EMPTY_SET, data.EMPTY_SET, legs)

    class Bank:
        name = "bank"

        def identify(self, filepath):
            return True

        def account(self, filepath):
            return "Assets:Checking"

        def extract(self, filepath, existing):
            return [txn()]

    class Single(Bank):
        def extract(self, filepath, existing):
            return txn()

    class OnlyOfx:
        def name(self):
            return "only-ofx"

        def identify(self, file):
            return False
""")


@pytest.mark.parametrize(
    ("config", "code", "said"),
    [
        (
            "[Bank(), OnlyOfx()]",
            2,
            "CONFIG entry OnlyOfx is a Beancount v2 importer (its name is a method); wrap it as "
            "beangulp.Adapter(OnlyOfx(...))",
        ),
        ("[Bank]", 2, "CONFIG lists the class Bank, not an importer; list an instance, Bank(...)."),
        (
            "[Single()]",
            1,
            "Importer bank extract() returned a Transaction instead of a list of Beancount directives; "
            "return [entry] for one.",
        ),
    ],
    ids=["legacy-beside-modern", "class", "one-directive"],
)
def test_a_misshapen_config_names_the_entry_and_fix(
    tmp_path: Path, bea_config_dir: Path, config: str, code: int, said: str
) -> None:
    (tmp_path / "main.bean").write_text("2026-01-01 open Assets:Checking USD\n2026-01-01 open Expenses:Food USD\n")
    (tmp_path / "bank.txt").write_text("x\n")
    (tmp_path / "imp.py").write_text(f"{IMPORTERS}\nCONFIG = {config}\n")

    result = runner.invoke(
        app,
        ["--no-input", "--file", str(tmp_path / "main.bean"), "import", str(tmp_path / "bank.txt")]
        + ["--config", str(tmp_path / "imp.py")],
    )

    assert result.exit_code == code, result.output
    assert said in " ".join(result.stderr.split())
    assert "Use the current Beangulp Importer interface (name property" not in result.stderr
