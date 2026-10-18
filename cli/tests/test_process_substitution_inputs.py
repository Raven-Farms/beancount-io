"""A `<(…)` input is read or refused accurately (w5/436).

Process substitution passes `/dev/fd/N`. `treeify` handed that name to a
child that could not open it (`OSError: Bad file descriptor`), `import`
called the existing path "not found", and `doctor` relayed upstream's "does
not exist".
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n'

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="/dev/fd names")


def _bea_with_pipe(books: Path, data: str, *args: str) -> subprocess.CompletedProcess[str]:
    """Run bea with `{pipe}` in `args` naming a held pipe, as `<(…)` does."""
    read, write = os.pipe()
    os.write(write, data.encode())
    os.close(write)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    try:
        return subprocess.run(
            [sys.executable, "-m", "cli.main", *(arg.replace("{pipe}", f"/dev/fd/{read}") for arg in args)],
            env=env,
            cwd=books,
            capture_output=True,
            text=True,
            timeout=120,
            stdin=subprocess.DEVNULL,
            pass_fds=(read,),
        )
    finally:
        os.close(read)


def test_treeify_reads_a_pipe_argument(tmp_path: Path) -> None:
    result = _bea_with_pipe(tmp_path, "Assets:Cash  5\nAssets:Bank  7\n", "treeify", "{pipe}")
    assert result.returncode == 0, result.stderr
    assert result.stdout == "`-- Assets\n    |-- Cash  5\n    `-- Bank  7\n"


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (
            ["-f", "main.bean", "import", "{pipe}", "--account", "Assets:Cash", "--csv", "date=Date,amount=Amount"],
            "Export /dev/fd/{fd} is a pipe, not a file. Save it to a file and import that file.",
        ),
        (
            ["doctor", "lex", "{pipe}"],
            "Ledger path /dev/fd/{fd} is a pipe, not a file. Save it to a file and pass that file.",
        ),
        (["doctor", "print-options", "{pipe}"], "Ledger path /dev/fd/{fd} is a pipe, not a file."),
    ],
    ids=["import", "doctor-lex", "doctor-print-options"],
)
def test_a_pipe_where_a_file_is_needed_is_named(tmp_path: Path, args: list[str], message: str) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    result = _bea_with_pipe(tmp_path, "Date,Amount\n2026-01-05,-5.00\n", *args)
    assert result.returncode == 2, result.stderr
    pipe = next(arg for arg in result.args if arg.startswith("/dev/fd/"))
    assert message.replace("/dev/fd/{fd}", pipe) in result.stderr
    assert "not found" not in result.stderr and "does not exist" not in result.stderr


def test_an_import_directory_and_a_missing_export_keep_their_own_words(tmp_path: Path) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "exports").mkdir()
    base = ["-f", "main.bean", "import"]
    tail = ["--account", "Assets:Cash", "--csv", "date=Date,amount=Amount"]
    directory = _bea_with_pipe(tmp_path, "", *base, str(tmp_path / "exports"), *tail)
    assert f"Export {tmp_path / 'exports'} is a directory, not a file. Name the export file inside it." in (
        directory.stderr
    )
    missing = _bea_with_pipe(tmp_path, "", *base, "nope.csv", *tail)
    assert "Export file not found:" in missing.stderr


@pytest.mark.parametrize(
    ("flag", "extra"),
    [("--rules", ["--csv", "date=Date,amount=Amount", "--account", "Assets:Cash"]), ("--config", [])],
    ids=["rules", "config"],
)
def test_a_piped_import_option_file_is_named(tmp_path: Path, flag: str, extra: list[str]) -> None:
    """The engine child reading `--rules`/`--config` does not inherit the descriptor (w5/582)."""
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "s.csv").write_text("Date,Amount\n2026-01-05,-5.00\n")

    result = _bea_with_pipe(tmp_path, "CONFIG = []\n", "-f", "main.bean", "import", "s.csv", *extra, flag, "{pipe}")

    assert result.returncode == 2, result.stderr
    pipe = next(arg for arg in result.args if arg.startswith("/dev/fd/"))
    assert f"{flag} {pipe} is a pipe, not a file. Save it to a file and pass that file." in result.stderr
    assert "Bad file descriptor" not in result.stderr and "not found" not in result.stderr
