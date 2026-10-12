"""`bea format` reads a symlinked root's includes beside the link, like every other command (w5/087).

It resolved the named path first and walked the closure from the link's
target, so a present include was reported missing, never formatted — and the
`-o` guard, blind to the real include, let an export replace it with exit 0.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app

runner = CliRunner()

ROOT = 'include "accounts.bean"\n2026-01-02 * "x"\n  Assets:A  1 USD\n  Assets:B  -1 USD\n'
ACCOUNTS = "2026-01-01 open Assets:A\n2026-01-01 open Assets:B\n"
MISALIGNED = (
    '2026-01-01 open Assets:A\n2026-01-01 open Assets:B\n2026-01-03 * "y"\n  Assets:A  1 USD\n  Assets:B  -1 USD\n'
)

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="needs symlinks")


@pytest.fixture(params=["symlink", "regular"])
def books(
    request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bea_config_dir: Path
) -> Path:
    directory = tmp_path / "books"
    directory.mkdir()
    if request.param == "symlink":
        (tmp_path / "store").mkdir()
        (tmp_path / "store" / "main-2026.bean").write_text(ROOT)
        (directory / "main.bean").symlink_to("../store/main-2026.bean")
    else:
        (directory / "main.bean").write_text(ROOT)
    (directory / "accounts.bean").write_text(ACCOUNTS)
    monkeypatch.chdir(tmp_path)
    return directory


def test_check_scans_the_include_beside_the_link(books: Path) -> None:
    result = runner.invoke(app, ["--json", "format", "--check", "books/main.bean"])

    payload = json.loads(result.stdout or result.stderr)
    data = payload.get("data") or payload["error"]["result"]
    assert data["missing"] == []
    assert data["scanned"] == 2
    assert runner.invoke(app, ["--file", "books/main.bean", "check"]).exit_code == 0


def test_in_place_formats_the_include_beside_the_link(books: Path) -> None:
    (books / "accounts.bean").write_text(MISALIGNED)

    result = runner.invoke(app, ["format", "-i", "books/main.bean"])

    assert result.exit_code == 0, result.output
    assert "missing include" not in result.output
    assert (books / "accounts.bean").read_text() != MISALIGNED
    assert (books / "main.bean").is_symlink() == (books.parent / "store").exists()
    assert runner.invoke(app, ["format", "--check", "books/main.bean"]).exit_code == 0


@pytest.mark.parametrize("how", ["positional", "global-file"])
def test_output_onto_the_include_is_refused(books: Path, how: str) -> None:
    named = ["format", "books/main.bean"] if how == "positional" else ["--file", "books/main.bean", "format"]

    result = runner.invoke(app, [*named, "-o", "books/accounts.bean"])

    assert result.exit_code == 2, result.output
    assert "would overwrite the ledger it reads" in " ".join(result.output.split())
    assert (books / "accounts.bean").read_text() == ACCOUNTS
    assert runner.invoke(app, ["--file", "books/main.bean", "check"]).exit_code == 0


def test_output_elsewhere_still_writes_the_formatted_root(books: Path) -> None:
    result = runner.invoke(app, ["format", "books/main.bean", "-o", "formatted.bean"])

    assert result.exit_code == 0, result.output
    assert 'include "accounts.bean"' in (books.parent / "formatted.bean").read_text()
