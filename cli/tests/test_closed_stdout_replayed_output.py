"""Commands that replay a child's output survive a closed stdout or stderr (w5/258).

w1/107 made a command exit 0 with fd 1 closed (`>&-`, as some schedulers and
service managers start jobs), but guarded only the final flush. `doctor`,
`treeify`, `example` and `query --source` write a captured child's output to
`sys.stdout` themselves, and Python sets that to None when the descriptor is
closed: each exited 1 with `'NoneType' object has no attribute 'write'`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """2024-01-01 open Assets:Bank USD
2024-01-01 open Expenses:Food USD
2024-01-02 * "x"
  Expenses:Food 1 USD
  Assets:Bank
"""

TREE = "Assets:Bank 1\nAssets:Cash 2\n"

#: Each command, and the text it reads on stdin when it reads any.
COMMANDS: dict[str, tuple[list[str], str | None]] = {
    "format": (["format", "m.bean"], None),
    "doctor-lex": (["doctor", "lex", "m.bean"], None),
    "doctor-context": (["doctor", "context", "m.bean", "3"], None),
    "doctor-missing-open": (["doctor", "missing-open", "m.bean"], None),
    "doctor-roundtrip": (["doctor", "roundtrip", "m.bean"], None),
    "query-source": (["query", "--source", "m.bean", "SELECT account"], None),
    "treeify": (["treeify"], TREE),
    "example": (["example", "--seed", "1"], None),
}

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="closes a standard descriptor via preexec_fn")


def _bea(
    tmp_path: Path, args: list[str], *, closed: int | None = None, text: str | None = None
) -> subprocess.CompletedProcess[str]:
    (tmp_path / "m.bean").write_text(LEDGER, encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        input=text,
        stdin=subprocess.DEVNULL if text is None else None,
        stdout=None if closed == 1 else subprocess.PIPE,
        stderr=None if closed == 2 else subprocess.PIPE,
        # The point is a child with that descriptor closed, not redirected.
        preexec_fn=None if closed is None else lambda: os.close(closed),  # noqa: PLW1509
        text=True,
        timeout=120,
    )


@pytest.mark.parametrize("name", COMMANDS)
def test_a_command_with_stdout_closed_exits_zero(tmp_path: Path, name: str) -> None:
    args, text = COMMANDS[name]

    done = _bea(tmp_path, args, closed=1, text=text)

    assert "NoneType" not in done.stderr
    assert done.returncode == 0, done.stderr


@pytest.mark.parametrize("name", COMMANDS)
def test_the_same_command_still_prints_to_an_open_stdout(tmp_path: Path, name: str) -> None:
    args, text = COMMANDS[name]

    done = _bea(tmp_path, args, text=text)

    assert done.returncode == 0, done.stderr
    # `roundtrip` and `missing-open` have nothing to say on stdout about clean books.
    assert bool(done.stdout.strip()) == (name not in {"doctor-roundtrip", "doctor-missing-open"})


def test_a_roundtrip_of_unparseable_books_with_stdout_closed_still_names_the_errors(tmp_path: Path) -> None:
    (tmp_path / "broken.bean").write_text(LEDGER + "2024-01-03 nonsense\n", encoding="utf-8")

    done = _bea(tmp_path, ["doctor", "roundtrip", "broken.bean"], closed=1)

    assert "NoneType" not in done.stderr
    assert done.returncode != 0
    assert "broken.bean" in done.stderr
    assert "Congratulations" not in done.stderr


def test_a_mistyped_query_with_stderr_closed_is_still_a_usage_error(tmp_path: Path) -> None:
    done = _bea(tmp_path, ["query", "--source", "m.bean", "SELEC"], closed=2)

    assert "NoneType" not in done.stdout
    assert done.returncode == 2
    assert done.stdout == ""


def test_a_query_with_stderr_closed_prints_its_answer_and_exits_zero(tmp_path: Path) -> None:
    done = _bea(tmp_path, ["query", "--source", "m.bean", "SELECT account"], closed=2)

    assert done.returncode == 0, done.stdout
    assert "Expenses:Food" in done.stdout
    assert "NoneType" not in done.stdout
