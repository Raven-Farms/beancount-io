"""Every include edge to one unreadable member is reported, while that member is read once (w5/709)."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Any

import pytest

from cli import output

ROOT = Path(__file__).resolve().parents[1]
FORMATTABLE = '2026-01-02 * "readable root"\n  Assets:Cash   1 USD\n  Equity:Opening -1 USD\n'
SHARED = "2026-01-01 open Assets:Cash USD\n2026-01-01 open Equity:Opening\n"
pytestmark = pytest.mark.skipif(
    sys.platform == "win32" or not hasattr(os, "geteuid") or os.geteuid() == 0,
    reason="requires POSIX permissions that bind the caller",
)


@contextmanager
def _unreadable(member: Path) -> Iterator[None]:
    original = stat.S_IMODE(member.stat().st_mode)
    member.chmod(0)
    try:
        assert not os.access(member, os.R_OK)
        yield
    finally:
        member.chmod(original)


def _shared(tmp_path: Path) -> tuple[list[Path], Path]:
    roots = [tmp_path / "first root.bean", tmp_path / "second root.bean"]
    for index, root in enumerate(roots):
        root.write_text('include "sub.bean"\n' + (FORMATTABLE if index == 0 else ""))
    member = tmp_path / "sub.bean"
    member.write_text(SHARED)
    return roots, member


def _format(tmp_path: Path, roots: list[Path], mode: str, *, as_json: bool) -> subprocess.CompletedProcess[str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_") and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_UPDATE_API_URL="http://127.0.0.1:9",
        BEA_TAP_FORMULA_URL="http://127.0.0.1:9/bea.rb",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
        TERM="dumb",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *(["--json"] if as_json else []), "format", mode, *map(str, roots)],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _missing(done: subprocess.CompletedProcess[str], mode: str) -> list[dict[str, Any]]:
    assert done.returncode == (0 if mode == "--dry-run" else 1), done.stdout + done.stderr
    payload = json.loads(done.stdout if mode == "--dry-run" else done.stderr)
    result = payload["data"] if mode == "--dry-run" else payload["error"]["result"]
    return result["missing"]


def _assert_edges(
    items: list[dict[str, Any]], expected: set[tuple[str, Path]], reason: str = "Permission denied"
) -> None:
    assert {(item["include"], Path(item["from"])) for item in items} == expected, items
    assert len(items) == len(expected), items
    assert all(reason in item["reason"] for item in items), items


@pytest.mark.parametrize("mode", ["--check", "--dry-run", "-i"])
@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
@pytest.mark.parametrize("reverse", [False, True], ids=["forward-roots", "reverse-roots"])
def test_each_root_names_its_own_unreadable_include_regardless_of_root_order(
    tmp_path: Path, mode: str, as_json: bool, reverse: bool
) -> None:
    roots, member = _shared(tmp_path)
    originals = {p: p.read_bytes() for p in [*roots, member]}
    with _unreadable(member):
        done = _format(tmp_path, roots[::-1] if reverse else roots, mode, as_json=as_json)

        assert done.returncode == (0 if mode == "--dry-run" else 1), done.stdout + done.stderr
        if as_json:
            _assert_edges(_missing(done, mode), {("sub.bean", root) for root in roots})
        else:
            text = done.stdout + done.stderr
            for root in roots:
                assert text.count(f'unreadable include: "sub.bean" (included by {root}):') == 1, text
            assert "Permission denied" in text and "Traceback" not in text
    assert member.read_bytes() == originals[member]
    if mode == "-i":
        # Existing partial-format policy: valid roots are still rewritten,
        # and the failed shared member is left alone.
        assert roots[0].read_bytes() != originals[roots[0]]
    else:
        assert {p: p.read_bytes() for p in originals} == originals


def test_overlapping_globs_report_each_distinct_pattern_once_per_source(tmp_path: Path) -> None:
    roots, member = _shared(tmp_path)
    roots[0].write_text('include "sub.bean"\ninclude "sub*.bean"\ninclude "sub.bean"\n')
    roots[1].write_text('include "sub.bean"\ninclude "s??.bean"\n')
    expected = {
        ("sub.bean", roots[0]),
        ("sub*.bean", roots[0]),
        ("sub.bean", roots[1]),
        ("s??.bean", roots[1]),
    }
    with _unreadable(member):
        done = _format(tmp_path, roots, "--check", as_json=True)

        _assert_edges(_missing(done, "--check"), expected)


def test_a_diamond_names_the_actual_nested_includers_once(tmp_path: Path) -> None:
    roots, member = _shared(tmp_path)
    left = tmp_path / "left.bean"
    right = tmp_path / "right.bean"
    left.write_text('include "sub.bean"\n')
    right.write_text('include "s??.bean"\n')
    roots[0].write_text('include "left.bean"\ninclude "right.bean"\n')
    roots[1].write_text('include "right.bean"\ninclude "left.bean"\n')
    with _unreadable(member):
        done = _format(tmp_path, roots, "--dry-run", as_json=True)

        _assert_edges(_missing(done, "--dry-run"), {("sub.bean", left), ("s??.bean", right)})


@pytest.mark.parametrize("reverse", [False, True], ids=["physical-first", "alias-first"])
def test_an_alias_to_the_same_unreadable_member_keeps_both_include_spellings(tmp_path: Path, reverse: bool) -> None:
    roots, member = _shared(tmp_path)
    alias = tmp_path / "alias.bean"
    alias.symlink_to(member.name)
    roots[1].write_text('include "alias.bean"\n')
    with _unreadable(member):
        done = _format(tmp_path, roots[::-1] if reverse else roots, "--check", as_json=True)

        items = _missing(done, "--check")
        _assert_edges(items, {("sub.bean", roots[0]), ("alias.bean", roots[1])})
        reasons = {item["from"]: item["reason"] for item in items}
        assert reasons[str(roots[0])] == f"{member} cannot be read: Permission denied"
        assert reasons[str(roots[1])] == f"{alias} cannot be read: Permission denied"


def test_a_shared_directory_keeps_the_existing_one_result_per_includer_policy(tmp_path: Path) -> None:
    roots, member = _shared(tmp_path)
    member.unlink()
    member.mkdir()

    done = _format(tmp_path, roots, "--check", as_json=True)

    _assert_edges(_missing(done, "--check"), {("sub.bean", root) for root in roots}, "directory, not a file")


@pytest.mark.parametrize("mode", ["--check", "--dry-run", "-i"])
def test_a_shared_readable_member_is_still_formatted_once_without_missing_results(tmp_path: Path, mode: str) -> None:
    roots, member = _shared(tmp_path)
    aligned = _format(tmp_path, roots, "-i", as_json=True)
    assert aligned.returncode == 0, aligned.stdout + aligned.stderr
    originals = {p: p.read_bytes() for p in [*roots, member]}

    done = _format(tmp_path, roots, mode, as_json=True)

    assert done.returncode == 0, done.stdout + done.stderr
    data = json.loads(done.stdout)["data"]
    assert data["missing"] == [] and data["scanned"] == 3
    assert data["formatted"] == []
    assert {p: p.read_bytes() for p in originals} == originals


@pytest.mark.parametrize("unreadable", [False, True], ids=["readable", "unreadable"])
def test_a_shared_walk_attempts_each_physical_member_only_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, unreadable: bool
) -> None:
    roots, member = _shared(tmp_path)
    alias = tmp_path / "alias.bean"
    alias.symlink_to(member.name)
    roots[1].write_text('include "alias.bean"\n')
    reads: Counter[Path] = Counter()
    original = Path.read_text

    def read_text(path: Path, *args: Any, **kwargs: Any) -> str:
        reads[path.resolve()] += 1
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    with _unreadable(member) if unreadable else nullcontext():
        members, missing = output.walk_closure(*roots)

    assert reads == Counter({roots[0]: 1, roots[1]: 1, member: 1})
    assert len(members) == 3
    if unreadable:
        assert {(item.include, item.source) for item in missing} == {("sub.bean", roots[0]), ("alias.bean", roots[1])}
        assert all("Permission denied" in (item.reason or "") for item in missing)
    else:
        assert missing == []


@pytest.mark.parametrize("reverse", [False, True], ids=["failed-root-first", "includer-first"])
def test_a_failed_explicit_root_is_still_reported_for_the_root_that_includes_it(tmp_path: Path, reverse: bool) -> None:
    roots, member = _shared(tmp_path)
    selected = [member, roots[0]]
    with _unreadable(member):
        _, missing = output.walk_closure(*(selected[::-1] if reverse else selected))

    assert len(missing) == 1
    assert (missing[0].include, missing[0].source) == ("sub.bean", roots[0])
    assert "Permission denied" in (missing[0].reason or "")
