"""Bare '-' is a treeify stream; './-' remains a literal guarded path (w5/705)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app
from tests.test_no_input_terminal_stdin import _on_a_terminal

ROOT = Path(__file__).resolve().parents[1]
ASSETS = b"Assets:Bank:Checking   10 USD\nAssets:Bank:Savings    20 USD\n"
EXPENSES = b"Expenses:Food:Dining   5 USD\nExpenses:Food:Grocery  6 USD\n"
LOOSE = b"foods:dining   5 USD\nfoods:grocery  6 USD\n"


def _env(tmp_path: Path) -> dict[str, str]:
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
    return env


def _treeify(tmp_path: Path, args: list[str], stdin: bytes = b"") -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", "treeify", *args],
        cwd=tmp_path,
        env=_env(tmp_path),
        input=stdin,
        capture_output=True,
        timeout=30,
    )


def _rendered(done: subprocess.CompletedProcess[bytes], names: list[str]) -> str:
    assert done.returncode == 0, done.stderr.decode("utf-8", errors="replace")
    assert done.stderr == b""
    text = done.stdout.decode()
    for name in names:
        assert name in text, text
    assert "|--" in text or "`--" in text, text
    return text


@pytest.mark.parametrize(
    ("options", "source", "names"),
    [
        (["-o", "-"], ASSETS, ["Assets", "Checking", "Savings"]),
        (["--output", "-"], ASSETS, ["Assets", "Checking", "Savings"]),
        (["--output=-"], ASSETS, ["Assets", "Checking", "Savings"]),
        (["-o-"], ASSETS, ["Assets", "Checking", "Savings"]),
        (["--outp=-"], ASSETS, ["Assets", "Checking", "Savings"]),
        (["-Ao-"], LOOSE, ["foods", "dining", "grocery"]),
        (["-r", r"[a-z]+(?::[a-z]+)+", "--output=-"], LOOSE, ["foods", "dining", "grocery"]),
    ],
    ids=["short", "long", "equals", "attached", "abbreviated", "clustered-loose", "custom-pattern"],
)
def test_dash_output_prints_the_tree_and_keeps_forwarded_options(
    tmp_path: Path, options: list[str], source: bytes, names: list[str]
) -> None:
    input_file = tmp_path / "accounts.txt"
    input_file.write_bytes(source)

    done = _treeify(tmp_path, [str(input_file), *options], EXPENSES)

    _rendered(done, names)
    assert not (tmp_path / "-").exists()
    assert input_file.read_bytes() == source


@pytest.mark.parametrize("args", [["-"], ["-", "-o", "-"], ["--output=-", "-"]], ids=["input", "both", "long-both"])
@pytest.mark.parametrize("stale_dash", [False, True], ids=["no-dash-file", "stale-dash-file"])
def test_explicit_dash_reads_piped_input_even_with_a_stale_literal_dash_file(
    tmp_path: Path, args: list[str], stale_dash: bool
) -> None:
    dash = tmp_path / "-"
    if stale_dash:
        dash.write_bytes(ASSETS)

    done = _treeify(tmp_path, args, EXPENSES)

    text = _rendered(done, ["Expenses", "Dining", "Grocery"])
    assert "Assets" not in text and "Checking" not in text
    if stale_dash:
        assert dash.read_bytes() == ASSETS
    else:
        assert not dash.exists()


def test_dot_slash_dash_input_is_still_a_literal_file(tmp_path: Path) -> None:
    dash = tmp_path / "-"
    dash.write_bytes(ASSETS)

    done = _treeify(tmp_path, ["./-", "-o", "-"], EXPENSES)

    text = _rendered(done, ["Assets", "Checking", "Savings"])
    assert "Expenses" not in text and dash.read_bytes() == ASSETS


def test_dot_slash_dash_output_is_still_a_literal_atomic_destination(tmp_path: Path) -> None:
    source = tmp_path / "accounts.txt"
    source.write_bytes(EXPENSES)
    dash = tmp_path / "-"
    dash.write_bytes(ASSETS)

    done = _treeify(tmp_path, [str(source), "-o", "./-"])

    assert done.returncode == 0, done.stderr.decode()
    assert done.stdout == b"" and done.stderr == b""
    rendered = dash.read_text()
    assert "Expenses" in rendered and "Dining" in rendered and "Grocery" in rendered
    assert "Assets" not in rendered
    assert source.read_bytes() == EXPENSES


def test_the_same_literal_dash_file_as_input_and_output_remains_refused(tmp_path: Path) -> None:
    dash = tmp_path / "-"
    dash.write_bytes(ASSETS)

    done = _treeify(tmp_path, ["./-", "--output=./-"], EXPENSES)

    assert done.returncode == 2, done.stderr.decode()
    assert done.stdout == b"" and dash.read_bytes() == ASSETS
    assert b"would overwrite the file it reads" in done.stderr


def test_non_utf8_explicit_stdin_names_stdin_and_preserves_literal_output(tmp_path: Path) -> None:
    dash = tmp_path / "-"
    dash.write_bytes(ASSETS)

    done = _treeify(tmp_path, ["-", "-o", "./-"], b"Expenses:Caf\xe9  5 EUR\n")

    assert done.returncode == 2, done.stderr.decode()
    assert done.stdout == b"" and dash.read_bytes() == ASSETS
    assert b"Cannot decode 'stdin' as UTF-8" in done.stderr
    assert b"UnicodeDecodeError" not in done.stderr


def test_literal_dash_output_honors_a_filesystem_write_access_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "accounts.txt"
    source.write_bytes(EXPENSES)
    dash = tmp_path / "-"
    dash.write_bytes(ASSETS)
    for name in tuple(os.environ):
        if name.startswith("BEA_"):
            monkeypatch.delenv(name)
    for name, value in _env(tmp_path).items():
        monkeypatch.setenv(name, value)
    monkeypatch.chdir(tmp_path)
    real_access = os.access

    def access(path: str | os.PathLike[str], mode: int, **kwargs: object) -> bool:
        # Writable mode bits do not prove that an ACL allows replacement.
        # Deny only this destination's write access, preserving real checks
        # for the engine interpreter, source file and every other path.
        if mode & os.W_OK and Path(path).absolute() == dash:
            return False
        return real_access(path, mode, **kwargs)

    monkeypatch.setattr(os, "access", access)

    done = CliRunner().invoke(app, ["treeify", str(source), "-o", "./-"])

    assert done.exit_code == 3, done.output
    assert done.stdout == ""
    assert "read-only and cannot be replaced" in done.stderr
    assert dash.read_bytes() == ASSETS and source.read_bytes() == EXPENSES


@pytest.mark.skipif(sys.platform == "win32", reason="needs a POSIX pseudo-terminal")
def test_no_input_explicit_dash_refuses_terminal_stdin_even_with_a_stale_file(tmp_path: Path) -> None:
    dash = tmp_path / "-"
    dash.write_bytes(ASSETS)

    code, screen = _on_a_terminal(tmp_path, ["--no-input", "treeify", "-", "-o", "-"])

    assert code == 2, screen
    assert "Input is required with --no-input" in screen
    assert dash.read_bytes() == ASSETS
