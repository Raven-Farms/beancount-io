"""`bea engine status` and the docs describe libmagic as optional for Beangulp.

Beangulp imports python-magic behind `except (ImportError, OSError)` in its
deprecated file-type helper and falls back to guessing by extension, so
`bea ingest` runs on a machine without the system library. Only an importer
that calls python-magic itself needs it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.engine import paths, provision
from cli.main import app

CLI_ROOT = Path(__file__).parent.parent
DOCS = ("README.md", "docs/USAGE.md", "docs/IMPORTING.md")
REQUIRED = re.compile(r"needs?\s+(the\s+)?system\s+libmagic|,\s*system\s+libmagic\s*,", re.IGNORECASE)


def test_engine_status_calls_libmagic_optional(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(paths.DIR_ENV, str(tmp_path / "engine"))
    monkeypatch.delenv(paths.PYTHON_ENV, raising=False)
    monkeypatch.setattr(provision, "provision", lambda _root: pytest.fail("status must not provision"))

    result = CliRunner().invoke(app, ["engine", "status"])

    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    note = lines[next(i for i, line in enumerate(lines) if line.startswith("  beangulp:")) + 1]
    assert "libmagic library is optional" in note
    assert "python-magic themselves" in note
    assert not REQUIRED.search(result.output)
    # The CSV-mapper half of the note is unchanged.
    assert "CSV import via --csv does not need this feature." in note


@pytest.mark.parametrize("doc", DOCS)
def test_docs_call_libmagic_optional(doc: str) -> None:
    text = (CLI_ROOT / doc).read_text(encoding="utf-8")
    mentions = [line for line in text.splitlines() if "libmagic" in line]

    assert mentions, f"{doc} no longer mentions libmagic"
    assert all("optional" in line for line in mentions), mentions
    assert not REQUIRED.search(text)
