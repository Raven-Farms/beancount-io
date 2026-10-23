"""A raising `identify()` names its importer and phase; a guarded one declines (w5/780).

The importer-author template opened files as UTF-8 with no guard, so a
Latin-1 export meant for another importer crashed the whole runner — and
`import --config` reported `Importer failed (UnicodeDecodeError)` without
saying whose `identify()` raised.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

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
        meta = data.new_metadata("giro.csv", 1)
        return data.Transaction(meta, datetime.date(2026, 5, 5), "*", None, "r",
                                data.EMPTY_SET, data.EMPTY_SET, legs)

    class Chase:
        name = "chase"
        encoding = "utf8"

        def identify(self, filepath):
            IDENTIFY

        def account(self, filepath):
            return "Assets:Checking"

        def extract(self, filepath, existing):
            return [txn()]

    class Giro:
        name = "giro"

        def identify(self, filepath):
            with open(filepath, encoding="latin-1") as f:
                return f.readline().strip().startswith("Buchungstag")

        def account(self, filepath):
            return "Assets:Checking"

        def extract(self, filepath, existing):
            return [txn()]
""")
UNGUARDED = "\n".join(
    [
        "with open(filepath) as f:",
        '            return f.readline().strip() == "Date,Description,Amount"',
    ]
)
GUARDED = "\n".join(
    [
        "try:",
        "            with open(filepath, encoding=self.encoding) as f:",
        '                return f.readline().strip() == "Date,Description,Amount"',
        "        except (OSError, UnicodeError):",
        "            return False",
    ]
)


def _books(tmp_path: Path, identify: str) -> list[str]:
    (tmp_path / "main.bean").write_text("2026-01-01 open Assets:Checking USD\n2026-01-01 open Expenses:Food USD\n")
    (tmp_path / "giro.csv").write_bytes(
        "Buchungstag;Verwendungszweck;Betrag\n05.05.2026;M\xdcLLER B\xc4CKEREI;-4,80\n".encode("latin-1")
    )
    (tmp_path / "imp.py").write_text(f"{IMPORTERS.replace('IDENTIFY', identify)}\nCONFIG = [Chase(), Giro()]\n")
    return [
        "--no-input",
        "--file",
        str(tmp_path / "main.bean"),
        "import",
        str(tmp_path / "giro.csv"),
        "--config",
        str(tmp_path / "imp.py"),
    ]


def test_a_raising_identify_names_the_importer_and_phase(tmp_path: Path, bea_config_dir: Path) -> None:
    result = runner.invoke(app, _books(tmp_path, UNGUARDED))

    assert result.exit_code == 1, result.output
    assert "Importer chase identify() raised UnicodeDecodeError" in " ".join(result.stderr.split())


def test_a_guarded_identify_lets_the_right_importer_claim(tmp_path: Path, bea_config_dir: Path) -> None:
    result = runner.invoke(app, _books(tmp_path, GUARDED))

    assert result.exit_code == 0, result.output
    assert "giro" in result.output and "1 ready" in result.output
