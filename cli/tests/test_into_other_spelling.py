"""`--into` spelled in another letter case or Unicode form is a usage error, not a conflict (w5/097).

On a case- and normalization-insensitive volume the differently spelled name
reaches the same file. It matched no snapshot member as text, the include glob
took it for a new file, and its existing on disk was reported as a concurrent
edit — exit 4, "retry" — that no retry could clear. w5/721 keeps the refusal
for a case-only respelling and for a composed spelling of an NFD file; a
decomposed spelling of an NFC file now writes it, as creation does.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

ROOT = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Checking USD\n2026-01-01 open Expenses:Food\n'
ENTRY = '2026-01-02 * "Lunch"\n  Expenses:Food  5.00 USD\n  Assets:Checking\n'
ADD = ["add", "transaction", "Dinner", "--date", "2026-01-03", "-p", "Expenses:Food 9 USD", "-p", "Assets:Checking"]


def _books(tmp_path: Path, name: str, include: str = "txns/*.bean") -> tuple[Path, Path]:
    (tmp_path / "txns").mkdir()
    root = tmp_path / "main.bean"
    root.write_text(ROOT + f'include "{include}"\n')
    member = tmp_path / "txns" / name
    member.write_text(ENTRY)
    return root, member


def _add(root: Path, into: str, *, as_json: bool = False) -> Any:
    return runner.invoke(app, [*(["--json"] if as_json else []), "--file", str(root), *ADD, "--into", into])


def _reaches(tmp_path: Path, other: str) -> bool:
    """Whether this volume answers to the other spelling at all."""
    return (tmp_path / "txns" / other).exists()


@pytest.mark.parametrize(
    ("on_disk", "typed"),
    [
        ("jan.bean", "Jan.bean"),
        (unicodedata.normalize("NFD", "café.bean"), unicodedata.normalize("NFC", "café.bean")),
    ],
    ids=["letter-case", "typed-composed"],
)
def test_another_spelling_of_an_included_file_is_a_usage_error(
    tmp_path: Path, bea_config_dir: Path, on_disk: str, typed: str
) -> None:
    root, member = _books(tmp_path, on_disk)
    if not _reaches(tmp_path, typed):
        pytest.skip("this volume keeps the two spellings apart")

    result = _add(root, f"txns/{typed}")
    as_json = _add(root, f"txns/{typed}", as_json=True)

    assert result.exit_code == 2, result.output
    flat = " ".join(result.output.split())
    assert "changed during the operation" not in flat
    assert "Nothing was written" in flat
    assert json.loads(as_json.stderr)["error"]["category"] == "usage"
    assert member.read_text() == ENTRY
    assert len(list((tmp_path / "txns").iterdir())) == 1


def test_a_decomposed_spelling_of_an_nfc_file_writes_it(tmp_path: Path, bea_config_dir: Path) -> None:
    """The NFD spelling pasted from Finder writes the NFC file, as creation does (w5/721)."""
    nfc = unicodedata.normalize("NFC", "café.bean")
    root, member = _books(tmp_path, nfc)
    typed = unicodedata.normalize("NFD", "café.bean")
    if not _reaches(tmp_path, typed):
        pytest.skip("this volume keeps the two spellings apart")

    result = _add(root, f"txns/{typed}")

    assert result.exit_code == 0, result.output
    assert '2026-01-03 * "Dinner"' in member.read_text()
    assert len(list((tmp_path / "txns").iterdir())) == 1


def test_the_exact_spelling_still_writes(tmp_path: Path, bea_config_dir: Path) -> None:
    root, member = _books(tmp_path, "jan.bean")

    result = _add(root, "txns/jan.bean")

    assert result.exit_code == 0, result.output
    assert '2026-01-03 * "Dinner"' in member.read_text()


def test_a_new_file_the_glob_matches_is_still_created(tmp_path: Path, bea_config_dir: Path) -> None:
    root, _ = _books(tmp_path, "jan.bean")

    result = _add(root, "txns/feb.bean")

    assert result.exit_code == 0, result.output
    assert '2026-01-03 * "Dinner"' in (tmp_path / "txns" / "feb.bean").read_text()


def test_a_file_that_appears_after_the_snapshot_is_still_a_conflict(tmp_path: Path) -> None:
    from bea_engine.ledger.write import LedgerSnapshot
    from bea_engine.protocol import ConflictError

    root, _ = _books(tmp_path, "jan.bean")
    snapshot = LedgerSnapshot.capture(root)
    (tmp_path / "txns" / "feb.bean").write_text(ENTRY)

    with pytest.raises(ConflictError):
        snapshot.require_target(tmp_path / "txns" / "feb.bean")
