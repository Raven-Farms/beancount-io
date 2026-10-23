"""Glob preflight visits only pattern-relevant directories and exposes their errors (w5/708)."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from bea_engine.include_glob import check_glob as engine_check
from cli.include_glob import check_glob as frontend_check


@pytest.fixture(params=[frontend_check, engine_check], ids=["frontend", "engine"])
def check(request: pytest.FixtureRequest) -> Callable[[str], None]:
    function: Callable[[str], None] = request.param
    return function


def _tree(tmp_path: Path) -> Path:
    root = tmp_path / "txns"
    for year in ("2025", "2026"):
        directory = root / year
        directory.mkdir(parents=True)
        (directory / "known.bean").write_text("; synthetic include\n")
    return root


@contextmanager
def _permissions(path: Path, mode: int) -> Iterator[None]:
    original = path.stat().st_mode
    path.chmod(mode)
    try:
        yield
    finally:
        path.chmod(original)


_PERMISSIONS = pytest.mark.skipif(
    sys.platform == "win32" or os.geteuid() == 0, reason="requires enforced POSIX directory permissions"
)


@_PERMISSIONS
@pytest.mark.parametrize(
    "pattern", ["**/*.bean", "*/*.bean", "20?5/*.bean", "202[45]/*.bean", "2025/*.bean", "**/", "**"]
)
def test_a_glob_that_visits_a_locked_directory_reports_its_path(
    tmp_path: Path, check: Callable[[str], None], pattern: str
) -> None:
    root = _tree(tmp_path)
    locked = root / "2025"
    with _permissions(locked, 0):
        with pytest.raises(PermissionError) as caught:
            check(str(root / pattern))
    assert caught.value.filename == str(locked)


@_PERMISSIONS
@pytest.mark.parametrize(
    "pattern", ["*.bean", "2026/*.bean", "2026/**/*.bean", "20?6/*.bean", "202[6-9]/*.bean", "missing/**/*.bean"]
)
def test_unmatched_or_nonrecursive_branches_do_not_scan_a_locked_nested_directory(
    tmp_path: Path, check: Callable[[str], None], pattern: str
) -> None:
    root = _tree(tmp_path)
    with _permissions(root / "2025", 0):
        assert check(str(root / pattern)) is None


@_PERMISSIONS
@pytest.mark.parametrize("pattern", ["2025/known.bean", "*/known.bean"])
def test_a_literal_filename_only_needs_search_access_to_its_directory(
    tmp_path: Path, check: Callable[[str], None], pattern: str
) -> None:
    root = _tree(tmp_path)
    with _permissions(root / "2025", 0o100):
        assert check(str(root / pattern)) is None


@_PERMISSIONS
def test_recursive_hidden_rules_and_explicit_hidden_components(tmp_path: Path, check: Callable[[str], None]) -> None:
    root = _tree(tmp_path)
    hidden = root / ".hidden"
    hidden.mkdir()
    with _permissions(hidden, 0):
        assert check(str(root / "**/*.bean")) is None
        assert check(str(root / "[.]hidden/*.bean")) is None
        for pattern in (".hidden/*.bean", ".*/*.bean"):
            with pytest.raises(PermissionError) as caught:
                check(str(root / pattern))
            assert caught.value.filename == str(hidden)


def test_recursive_directory_symlink_cycles_are_bounded_without_hiding_another_pattern_phase(
    tmp_path: Path, check: Callable[[str], None]
) -> None:
    root = _tree(tmp_path)
    (root / "2026" / "loop").symlink_to(root, target_is_directory=True)
    assert check(str(root / "**/**/known.bean")) is None
    assert check(str(root / "**/../*/known.bean")) is None


@_PERMISSIONS
def test_directory_symlinks_expose_relevant_errors_without_inspecting_unmatched_targets(
    tmp_path: Path, check: Callable[[str], None]
) -> None:
    root = _tree(tmp_path)
    locked = root / "2025"
    (locked / "inner").mkdir()
    link = root / "unmatched"
    link.symlink_to(locked / "inner", target_is_directory=True)
    with _permissions(locked, 0):
        assert check(str(root / "202[6]/*.bean")) is None
        with pytest.raises(PermissionError):
            check(str(link / "*.bean"))


def test_missing_paths_files_and_symlink_loops_keep_native_no_match_behavior(
    tmp_path: Path, check: Callable[[str], None]
) -> None:
    root = _tree(tmp_path)
    loop = root / "self"
    loop.symlink_to(loop)
    for pattern in ("missing/*.bean", "2026/known.bean/*.bean", "self/*.bean", "self", ""):
        assert check(str(root / pattern) if pattern else "") is None
