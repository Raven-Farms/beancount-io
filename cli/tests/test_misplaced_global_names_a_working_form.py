"""A misplaced global on `doctor`, `treeify` or `example` names a form that works (w5/620).

The generic "Place -f before the command" and "Place --json before the
command" sent these commands to a dead end: they ignore `--file` (they take
the file as an argument, or read none) and have no JSON output.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
        check=False,
    )


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text('option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n')
    (tmp_path / "bal.txt").write_text("Assets:Cash  5\n")
    return tmp_path


@pytest.mark.parametrize(
    ("args", "suggested"),
    [
        (["doctor", "print-options", "-f", "main.bean"], "bea doctor print-options main.bean"),
        (["doctor", "context", "--file=main.bean", "2"], "bea doctor context main.bean 2"),
        (["treeify", "-f", "bal.txt"], "bea treeify bal.txt"),
    ],
    ids=["doctor", "doctor-with-location", "treeify"],
)
def test_file_on_a_command_that_takes_it_as_an_argument(books: Path, args: list[str], suggested: str) -> None:
    refused = _bea(books, *args)

    assert refused.returncode == 2, refused.stderr
    assert f"takes the {'file' if args[0] == 'treeify' else 'ledger'} as an argument" in refused.stderr
    # No sentence period glued onto the command (w5/839).
    assert refused.stderr.rstrip().endswith(f": {suggested}")
    assert _bea(books, *shlex.split(suggested)[1:]).returncode == 0


@pytest.mark.parametrize(
    "args", [["doctor", "lex", "main.bean", "--json"], ["example", "--json"]], ids=["doctor", "example"]
)
def test_json_on_a_command_without_json_output(books: Path, args: list[str]) -> None:
    refused = _bea(books, *args)

    assert refused.returncode == 2, refused.stderr
    assert (
        f"bea {' '.join(args[:2]) if args[0] == 'doctor' else 'example'} has no JSON output; drop --json."
        in refused.stderr
    )
    assert "Place --json before the command" not in refused.stderr


def test_file_on_example_is_called_meaningless(books: Path) -> None:
    refused = _bea(books, "example", "-f", "main.bean")

    assert refused.returncode == 2, refused.stderr
    assert "bea example reads no ledger, so -f does nothing here; drop it." in refused.stderr


# ── gaps after w5/620 (w5/839) ───────────────────────────────────────────


@pytest.mark.parametrize(
    ("args", "said", "works"),
    [
        (
            ["doctor", "list-options", "-f", "main.bean"],
            "bea doctor list-options reads no ledger, so -f does nothing here; drop it.",
            ["doctor", "list-options"],
        ),
        (
            ["doctor", "-f", "main.bean", "lex"],
            "bea doctor operations take the ledger as an argument, not -f: bea doctor lex main.bean",
            ["doctor", "lex", "main.bean"],
        ),
        (
            ["doctor", "--json", "lex", "main.bean"],
            "bea doctor has no JSON output; drop --json.",
            ["doctor", "lex", "main.bean"],
        ),
        (
            ["doctor", "directories", "-f", "main.bean", "."],
            "bea doctor directories takes the ledger as an argument, not -f: bea doctor directories main.bean .",
            ["doctor", "directories", "main.bean", "."],
        ),
    ],
    ids=["list-options", "file-before-op", "json-before-op", "no-glued-period"],
)
def test_the_hinted_doctor_form_runs(books: Path, args: list[str], said: str, works: list[str]) -> None:
    refused = _bea(books, *args)

    assert refused.returncode == 2, refused.stderr
    assert said in " ".join(refused.stderr.split())
    assert "No such command" not in refused.stderr
    assert _bea(books, *works).returncode == 0


def test_json_after_the_bean_price_forward_says_to_drop_it(books: Path) -> None:
    refused = _bea(books, "price", "main.bean", "--json")

    assert refused.returncode == 2, refused.stderr
    assert "bea price has no JSON output; drop --json." in refused.stderr
    assert "Place --json before the command" not in refused.stderr
