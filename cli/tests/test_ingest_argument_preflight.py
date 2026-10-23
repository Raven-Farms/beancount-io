"""Ingest rejects bad ledger/output paths before executing the user's importer (w5/706)."""

from __future__ import annotations

import os
import shlex
import stat
import sys
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.main import app
from tests.test_ingest_noncanonical_existing import Books, _books

pytestmark = pytest.mark.usefixtures("use_optional_engine")


def _extract(books: Books, extra: list[str]) -> Any:
    return CliRunner().invoke(app, ["ingest", "extract", "--config", str(books.script), *extra, str(books.source)])


def _unchanged(books: Books) -> None:
    assert not books.marker.exists()
    assert {p: p.read_bytes() for p in books.originals} == books.originals


@pytest.mark.parametrize(
    ("spelling", "root_name", "symlink"),
    [
        ("short", "main.bean", False),
        ("equals", "main.beancount", False),
        ("clustered", None, False),
        ("short", "main.bean", True),
        ("equals", "main.beancount", True),
    ],
    ids=["short-bean", "equals-beancount", "clustered-fallback", "symlink-bean", "symlink-beancount"],
)
def test_an_existing_directory_names_a_shell_quoted_root_before_any_importer_runs(
    tmp_path: Path, spelling: str, root_name: str | None, symlink: bool
) -> None:
    books = _books(tmp_path, kind="clean", location="include")
    directory = books.root.parent
    if root_name is not None:
        candidate = directory / root_name
        candidate.write_bytes(books.root.read_bytes())
        books.originals[candidate] = candidate.read_bytes()
    if symlink:
        link = tmp_path / "books' link"
        link.symlink_to(directory, target_is_directory=True)
        directory = link
    extra = {
        "short": ["-e", str(directory)],
        "equals": [f"--existing={directory}"],
        "clustered": ["-qe", str(directory)],
    }[spelling]
    destination = tmp_path / "extract.txt"

    done = _extract(books, [*extra, "-o", str(destination)])

    assert done.exit_code == 2, done.output
    assert done.stdout == ""
    assert "--existing" in done.stderr and "directory" in done.stderr
    hint = ["--existing", str(directory / (root_name or "main.bean"))]
    assert shlex.join(hint) in done.stderr
    assert "Traceback" not in done.stderr and "IsADirectoryError" not in done.stderr
    assert not destination.exists()
    _unchanged(books)
    if root_name is not None:
        repaired = _extract(books, hint)
        assert repaired.exit_code == 0, repaired.output
        assert "; duplicate of" in repaired.stdout and "Salary" in repaired.stdout
        assert books.marker.read_text() == "loaded\n"
        assert {p: p.read_bytes() for p in books.originals} == books.originals


@pytest.mark.parametrize("kind", ["missing", "dangling-link", "device"])
def test_a_missing_or_nonregular_existing_path_refuses_before_script_execution(tmp_path: Path, kind: str) -> None:
    books = _books(tmp_path, kind="clean", location="include")
    if kind == "device":
        if sys.platform == "win32":
            pytest.skip("requires the POSIX null device")
        path = Path("/dev/null")
    else:
        path = tmp_path / "missing existing.bean"
        if kind == "dangling-link":
            path.symlink_to(tmp_path / "no-target.bean")

    done = _extract(books, ["-e", str(path)])

    assert done.exit_code == 2, done.output
    assert done.stdout == "" and "--existing" in done.stderr
    assert str(path) in done.stderr
    assert "Traceback" not in done.stderr
    _unchanged(books)
    if kind == "dangling-link":
        assert path.is_symlink() and not path.exists()


@pytest.mark.skipif(sys.platform == "win32" or os.geteuid() == 0, reason="requires enforced POSIX mode permissions")
@pytest.mark.parametrize("kind", ["parent", "file", "literal-dash"])
def test_unwritable_output_refuses_with_permission_status_before_loading_the_importer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    books = _books(tmp_path, kind="clean", location="include")
    sentinel = b"prior extract must survive\n"
    if kind == "parent":
        holder = tmp_path / "read-only output"
        holder.mkdir()
        destination = holder / "extract.txt"
        permission_path = holder
        original_mode = stat.S_IMODE(holder.stat().st_mode)
        holder.chmod(0o555)
        option = ["-qo", str(destination)]
    else:
        destination = tmp_path / ("-" if kind == "literal-dash" else "extract.txt")
        destination.write_bytes(sentinel)
        permission_path = destination
        original_mode = stat.S_IMODE(destination.stat().st_mode)
        destination.chmod(0o444)
        if kind == "literal-dash":
            monkeypatch.chdir(tmp_path)
            option = ["-o", "./-"]
        else:
            option = [f"--output={destination}"]
    try:
        done = _extract(books, ["-e", str(books.root), *option])

        assert done.exit_code == 3, done.output
        assert done.stdout == ""
        assert "not writable" in done.stderr or "read-only" in done.stderr
        assert "Nothing was written" in done.stderr
        assert "Traceback" not in done.stderr
        _unchanged(books)
        if kind == "parent":
            assert not destination.exists()
        else:
            assert destination.read_bytes() == sentinel
    finally:
        permission_path.chmod(original_mode)


@pytest.mark.parametrize("kind", ["missing-parent", "directory"])
def test_an_invalid_output_path_is_a_usage_refusal_before_any_extraction(tmp_path: Path, kind: str) -> None:
    books = _books(tmp_path, kind="clean", location="include")
    destination = tmp_path / "output"
    if kind == "directory":
        destination.mkdir()
        kept = destination / "kept.txt"
        kept.write_text("keep me")
    else:
        destination = destination / "extract.txt"

    done = _extract(books, ["--existing", str(books.root), "-o", str(destination)])

    assert done.exit_code == 2, done.output
    assert done.stdout == "" and "--output" in done.stderr
    assert "parent directory does not exist" in done.stderr if kind == "missing-parent" else "directory" in done.stderr
    assert "Traceback" not in done.stderr
    _unchanged(books)
    if kind == "missing-parent":
        assert not destination.parent.exists()
    else:
        assert kept.read_text() == "keep me"


@pytest.mark.parametrize("kind", ["new-file", "existing-file", "stdout"])
def test_valid_output_paths_still_run_real_extraction_and_duplicate_detection(tmp_path: Path, kind: str) -> None:
    books = _books(tmp_path, kind="clean", location="include")
    destination = tmp_path / "extract.txt"
    if kind == "existing-file":
        destination.write_text("prior extraction")
    output_args = ["-o", "-"] if kind == "stdout" else ["-o", str(destination)]

    done = _extract(books, ["-e", str(books.root), *output_args])

    assert done.exit_code == 0, done.output
    text = done.stdout if kind == "stdout" else destination.read_text()
    assert "Coffee" in text and "Salary" in text and "; duplicate of" in text
    assert books.marker.read_text() == "loaded\n"
    assert {p: p.read_bytes() for p in books.originals} == books.originals
    assert not (tmp_path / "-").exists()


def test_stdout_is_not_an_alias_of_an_existing_ledger_literally_named_dash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    books = _books(tmp_path, kind="clean", location="include")
    dash = books.root.parent / "-"
    dash.write_bytes(books.root.read_bytes())
    books.originals[dash] = dash.read_bytes()
    monkeypatch.chdir(dash.parent)

    done = _extract(books, ["-e", "./-", "-o", "-"])

    assert done.exit_code == 0, done.output
    assert "Coffee" in done.stdout and "; duplicate of" in done.stdout
    assert books.marker.read_text() == "loaded\n"
    assert {p: p.read_bytes() for p in books.originals} == books.originals


def test_archive_still_accepts_a_directory_destination(tmp_path: Path) -> None:
    books = _books(tmp_path, kind="clean", location="include")
    destination = tmp_path / "documents"
    destination.mkdir()

    done = CliRunner().invoke(
        app,
        ["ingest", "archive", "--config", str(books.script), str(books.source), "-n", "-o", str(destination)],
    )

    assert done.exit_code == 0, done.output
    assert books.marker.read_text() == "loaded\n"
    assert not list(destination.iterdir())
    assert {p: p.read_bytes() for p in books.originals} == books.originals
