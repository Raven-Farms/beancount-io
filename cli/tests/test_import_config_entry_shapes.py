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
            "CONFIG entry OnlyOfx has a name method, as a Beancount v2 importer does; make name a property",
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


def _preview(tmp_path: Path, importers: str, config: str) -> tuple[int, str]:
    (tmp_path / "main.bean").write_text("2026-01-01 open Assets:Checking USD\n2026-01-01 open Expenses:Food USD\n")
    (tmp_path / "bank.txt").write_text("x\n")
    (tmp_path / "imp.py").write_text(f"{importers}\nCONFIG = {config}\n")
    before = (tmp_path / "main.bean").read_bytes()
    result = runner.invoke(
        app,
        ["--no-input", "--file", str(tmp_path / "main.bean"), "import", str(tmp_path / "bank.txt")]
        + ["--config", str(tmp_path / "imp.py")],
    )
    assert (tmp_path / "main.bean").read_bytes() == before
    return result.exit_code, " ".join((result.stdout + result.stderr).split())


@pytest.mark.parametrize(
    ("config", "said"),
    [
        ("[Bank(), None]", "CONFIG entry 2 is None, not an importer: it has no identify/account/extract methods."),
        ("[lambda: Bank()]", "CONFIG entry 1 is a function, not an importer: it has no identify/account/extract"),
        ('["bank"]', "CONFIG entry 1 is a str, not an importer: it has no identify/account/extract methods."),
    ],
    ids=["none", "factory", "string"],
)
def test_a_config_entry_that_is_no_importer_is_named_before_any_runs(
    tmp_path: Path, bea_config_dir: Path, config: str, said: str
) -> None:
    """None, a factory or a string reached identify() and failed as a bare AttributeError (w5/857)."""
    code, text = _preview(tmp_path, IMPORTERS, config)

    assert code == 2, text
    assert said in text
    assert "AttributeError" not in text
    if "lambda" in config:
        assert "CONFIG = [factory()]" in text


def test_an_extract_returning_a_number_names_the_importer(tmp_path: Path, bea_config_dir: Path) -> None:
    importers = IMPORTERS + "\nclass Zero(Bank):\n    def extract(self, filepath, existing):\n        return 0\n"

    code, text = _preview(tmp_path, importers, "[Zero()]")

    assert code == 1, text
    assert "Importer bank extract() returned a int instead of a list of Beancount directives." in text
    assert "not iterable" not in text


def test_a_valid_importer_beside_an_unrelated_one_still_previews(tmp_path: Path, bea_config_dir: Path) -> None:
    importers = (
        IMPORTERS
        + "\nclass Other(Bank):\n    name = 'other'\n    def identify(self, filepath):\n"
        + ("        return False\n")
    )

    code, text = _preview(tmp_path, importers, "[Bank(), Other()]")

    assert code == 0, text
    assert "1 ready" in text


BEANGULP = textwrap.dedent("""
    import beangulp
    from beangulp.importer import ImporterProtocol

    class Modern(beangulp.Importer):
        def name(self):
            return "modern"

        def identify(self, filepath):
            return True

        def account(self, filepath):
            return "Assets:Checking"

        def extract(self, filepath, existing):
            return [txn()]

    class Legacy(ImporterProtocol):
        def name(self):
            return "legacy"

        def identify(self, file):
            return True

        def file_account(self, file):
            return "Assets:Checking"

        def extract(self, file, existing_entries=None):
            return [txn()]
""")


#: The shapes of beangulp 0.2's `beangulp.importer` this refusal tells apart,
#: imported beside the config: the test engine does not carry beangulp.
STAND_IN = textwrap.dedent("""
    import abc

    class Importer(abc.ABC):
        @property
        def name(self):
            return type(self).__name__

    class ImporterProtocol:
        def name(self):
            return type(self).__name__

    class Adapter(Importer):
        def __init__(self, importer):
            assert isinstance(importer, ImporterProtocol)
            self.importer = importer

        @property
        def name(self):
            return self.importer.name()

        def identify(self, filepath):
            return self.importer.identify(filepath)

        def account(self, filepath):
            return self.importer.file_account(filepath)

        def extract(self, filepath, existing):
            return self.importer.extract(filepath, existing)
""")


@pytest.mark.parametrize(
    ("config", "code", "said"),
    [
        ("[Modern()]", 2, "CONFIG entry Modern is a beangulp.Importer whose name is a method; beangulp reads it"),
        ("[Legacy()]", 2, "CONFIG entry Legacy is a Beancount v2 importer (its name is a method); wrap it as"),
        ("[beangulp.Adapter(Legacy())]", 0, "1 ready"),
    ],
    ids=["modern-name-method", "legacy", "legacy-adapted"],
)
def test_name_method_advice_works_for_the_importer_it_names(
    tmp_path: Path, bea_config_dir: Path, config: str, code: int, said: str
) -> None:
    """Adapter was proposed for a modern importer missing @property, and then crashed (w5/857)."""
    (tmp_path / "beangulp").mkdir()
    (tmp_path / "beangulp" / "importer.py").write_text(STAND_IN)
    (tmp_path / "beangulp" / "__init__.py").write_text("from beangulp.importer import Adapter, Importer\n")
    exit_code, text = _preview(tmp_path, IMPORTERS + BEANGULP, config)

    assert exit_code == code, text
    assert said in text
    assert "AssertionError" not in text
    if "Modern" in config:
        assert "add @property above Modern.name" in text and "Adapter" not in text
