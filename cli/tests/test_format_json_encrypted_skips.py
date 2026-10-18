"""Formatter walk results name encrypted members skipped without decrypting them (w5/686)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from cli.engine import launch
from cli.errors import ConflictError
from cli.main import app

ROOT = Path(__file__).resolve().parents[1]
REASON = "it is encrypted, and Beancount decrypts it only to load it."
ALIGNED = b"2026-01-01 open Assets:Cash USD\n"
MISALIGNED = b'2026-01-02 * "Coffee"\n   Expenses:Food 1.00 USD\n   Assets:Cash -1.00 USD\n'
MODES = ["--check", "--dry-run", "-i"]


def _fake_gpg(tmp_path: Path) -> Path:
    binary = tmp_path / "bin" / "gpg"
    binary.parent.mkdir(exist_ok=True)
    marker = tmp_path / "GPG_EXECUTED"
    binary.write_text(
        f"#!{sys.executable}\nfrom pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('executed')\nraise SystemExit(77)\n"
    )
    binary.chmod(0o755)
    return marker


def _cipher(tmp_path: Path, suffix: str = ".gpg", *, name: str = "secret") -> Path:
    path = tmp_path / f"{name}.bean{suffix}"
    path.write_bytes(
        b"-----BEGIN PGP MESSAGE-----\nsynthetic ciphertext\n-----END PGP MESSAGE-----\n"
        if suffix == ".asc"
        else b"\x85\xff\x00synthetic ciphertext\n"
    )
    return path


def _skip(*files: Path) -> list[dict[str, str]]:
    return [{"file": str(file.resolve()), "reason": REASON} for file in sorted(files)]


def _bea(tmp_path: Path, mode: str, root: Path, *, as_json: bool = True) -> subprocess.CompletedProcess[str]:
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
        PYTHONPATH=str(ROOT / "src"),
        PATH=os.pathsep.join([str(tmp_path / "bin"), os.environ["PATH"]]),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *(["--json"] if as_json else []), "format", mode, str(root)],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _result(done: subprocess.CompletedProcess[str], code: int) -> dict[str, Any]:
    assert done.returncode == code, done.stdout + done.stderr
    if code:
        assert done.stdout == ""
        error = json.loads(done.stderr)["error"]
        assert error["exit_code"] == code
        return dict(error["result"])
    assert done.stderr == "", done.stderr
    return dict(json.loads(done.stdout)["data"])


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("changed", [False, True], ids=["aligned", "needs-formatting"])
@pytest.mark.parametrize("suffix", [".gpg", ".asc"], ids=["gpg", "armored-asc"])
def test_each_json_walk_mode_reports_encrypted_skips_without_changing_its_exit_policy(
    tmp_path: Path, mode: str, changed: bool, suffix: str
) -> None:
    marker = _fake_gpg(tmp_path)
    cipher = _cipher(tmp_path, suffix)
    root = tmp_path / "main.bean"
    root.write_bytes(f'include "{cipher.name}"\n'.encode() + ALIGNED + (MISALIGNED if changed else b""))
    before, encrypted = root.read_bytes(), cipher.read_bytes()

    done = _bea(tmp_path, mode, root)
    data = _result(done, int(mode == "--check" and changed))

    assert data["skipped"] == _skip(cipher), data
    assert data["scanned"] == 1 and data["failed"] == data["missing"] == [], data
    assert data["formatted"] == ([str(root)] if changed else []), data
    assert (root.read_bytes() != before) == (mode == "-i" and changed)
    assert cipher.read_bytes() == encrypted and not marker.exists()


@pytest.mark.parametrize("mode", MODES)
def test_plain_asc_include_is_formatted_as_text_and_skipped_is_explicitly_empty(tmp_path: Path, mode: str) -> None:
    marker = _fake_gpg(tmp_path)
    root = tmp_path / "main.bean"
    root.write_text('include "plain.asc"\n')
    included = tmp_path / "plain.asc"
    included.write_bytes(ALIGNED)
    before = {path: path.read_bytes() for path in (root, included)}

    data = _result(_bea(tmp_path, mode, root), 0)

    assert data["skipped"] == [] and data["scanned"] == 2, data
    assert data["formatted"] == data["failed"] == data["missing"] == [], data
    assert {path: path.read_bytes() for path in before} == before
    assert not marker.exists()


def test_nested_globs_and_repeated_spelling_report_each_resolved_encrypted_member_once(tmp_path: Path) -> None:
    marker = _fake_gpg(tmp_path)
    gpg, asc = _cipher(tmp_path), _cipher(tmp_path, ".asc", name="armored")
    (tmp_path / "nested").mkdir()
    root = tmp_path / "main.bean"
    root.write_text(f'include "{gpg.name}"\ninclude "nested/*.bean"\n')
    included = tmp_path / "nested" / "child.bean"
    included.write_text(f'include "../{gpg.name}"\ninclude "../*.gpg"\ninclude "../{asc.name}"\n')
    before = {path: path.read_bytes() for path in (root, included, gpg, asc)}

    data = _result(_bea(tmp_path, "--check", root), 0)

    assert data["skipped"] == _skip(gpg, asc), data
    assert data["scanned"] == 2 and data["failed"] == data["missing"] == [], data
    assert {path: path.read_bytes() for path in before} == before
    assert not marker.exists()


@pytest.mark.parametrize("mode", ["--check", "-i"])
@pytest.mark.parametrize("problem", ["syntax", "missing"])
def test_failure_results_retain_the_skipped_member(tmp_path: Path, mode: str, problem: str) -> None:
    marker = _fake_gpg(tmp_path)
    cipher = _cipher(tmp_path)
    root = tmp_path / "main.bean"
    root.write_text(f'include "{cipher.name}"\ninclude "bad.bean"\n')
    if problem == "syntax":
        (tmp_path / "bad.bean").write_text("not beancount\n")
    before = {path: path.read_bytes() for path in tmp_path.glob("*.bean*")}

    data = _result(_bea(tmp_path, mode, root), 1)

    assert data["skipped"] == _skip(cipher), data
    if problem == "syntax":
        assert [failure["file"] for failure in data["failed"]] == [str(tmp_path / "bad.bean")], data
        assert data["missing"] == []
    else:
        assert [failure["include"] for failure in data["missing"]] == ["bad.bean"], data
        assert data["failed"] == []
    assert {path: path.read_bytes() for path in before} == before
    assert not marker.exists()


def test_dry_run_reports_skips_alongside_syntax_and_missing_includes_without_changing_status(tmp_path: Path) -> None:
    marker = _fake_gpg(tmp_path)
    cipher = _cipher(tmp_path)
    root = tmp_path / "main.bean"
    root.write_text(f'include "{cipher.name}"\ninclude "bad.bean"\ninclude "absent.bean"\n')
    (tmp_path / "bad.bean").write_text("not beancount\n")
    before = {path: path.read_bytes() for path in tmp_path.glob("*.bean*")}

    data = _result(_bea(tmp_path, "--dry-run", root), 0)

    assert data["skipped"] == _skip(cipher), data
    assert len(data["failed"]) == len(data["missing"]) == 1, data
    assert {path: path.read_bytes() for path in before} == before
    assert not marker.exists()


def test_a_real_partial_write_failure_retains_skips_and_exact_progress(tmp_path: Path) -> None:
    marker = _fake_gpg(tmp_path)
    cipher = _cipher(tmp_path)
    root = tmp_path / "00-main.bean"
    children = [tmp_path / name for name in ("10-first.bean", "20-read-only.bean", "30-later.bean")]
    root.write_text("".join(f'include "{path.name}"\n' for path in [*children, cipher]))
    for path in children:
        path.write_bytes(MISALIGNED)
    before = {path: path.read_bytes() for path in (root, *children, cipher)}
    children[1].chmod(0o444)
    try:
        data = _result(_bea(tmp_path, "-i", root), 3)
    finally:
        children[1].chmod(0o644)

    assert data["skipped"] == _skip(cipher), data
    assert data["scanned"] == 4 and data["formatted"] == [str(children[0])], data
    assert data["unchanged"] == [str(root)] and data["not_attempted"] == [str(children[2])], data
    assert [failure["file"] for failure in data["failed"]] == [str(children[1])], data
    assert children[0].read_bytes() != before[children[0]]
    assert all(path.read_bytes() == content for path, content in before.items() if path != children[0])
    assert not marker.exists()


def test_a_lost_engine_response_names_known_skips_without_inventing_a_progress_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    marker = _fake_gpg(tmp_path)
    cipher = _cipher(tmp_path)
    root = tmp_path / "main.bean"
    root.write_bytes(f'include "{cipher.name}"\n'.encode() + MISALIGNED)
    before = {path: path.read_bytes() for path in (root, cipher)}
    real = launch.helper_json

    def lose_response(args: Sequence[str], *, stdin: str | None = None, writes: bool = False) -> dict[str, Any]:
        if args[0] == "format" and "--in-place" in args:
            raise ConflictError("The engine response was lost; the write outcome is unknown.")
        return real(args, stdin=stdin, writes=writes)

    monkeypatch.setattr(launch, "helper_json", lose_response)
    monkeypatch.setenv("PATH", os.pathsep.join([str(tmp_path / "bin"), os.environ["PATH"]]))
    done = CliRunner().invoke(app, ["--json", "format", "-i", str(root)])

    assert done.exit_code == 4, done.output
    assert done.stdout == ""
    error = json.loads(done.stderr)["error"]
    assert "outcome is unknown" in error["message"]
    assert "result" not in error, error
    assert str(cipher) in " ".join(error["details"]), error
    assert {path: path.read_bytes() for path in before} == before
    assert not marker.exists()


def test_human_mode_keeps_naming_the_encrypted_skip_without_decrypting(tmp_path: Path) -> None:
    marker = _fake_gpg(tmp_path)
    cipher = _cipher(tmp_path)
    root = tmp_path / "main.bean"
    root.write_bytes(f'include "{cipher.name}"\n'.encode() + ALIGNED)
    before = {path: path.read_bytes() for path in (root, cipher)}

    done = _bea(tmp_path, "--check", root, as_json=False)

    assert done.returncode == 0, done.stdout + done.stderr
    assert f"Skipped {cipher}: {REASON}" in done.stderr
    assert {path: path.read_bytes() for path in before} == before
    assert not marker.exists()
