"""Writers whose `XDG_CACHE_HOME` differs still serialize (w5/181).

The write lock is a file under each caller's own cache directory, so two OS
users, containers or sandboxes on one ledger locked different files. Only the
compare-before-replace check stood between them, and it left a window of a few
milliseconds: eight concurrent `bea add transaction` runs could all print
"Added 1 transaction" and exit 0 with some of the transactions missing.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from bea_engine.ledger import write

ROOT = Path(__file__).resolve().parents[1]

LEDGER = 'option "operating_currency" "USD"\n2024-01-01 open Assets:Cash USD\n2024-01-01 open Expenses:Food USD\n'
WRITERS = 8

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="a directory cannot be locked on Windows")

# A writer in another process, with its own cache: exit 7 while it is still
# waiting after the grace period, 0 once its write is done.
WRITER = """\
import os, sys, threading
from pathlib import Path
from bea_engine.ledger import formatting, write

action, file = sys.argv[1], Path(sys.argv[2])
done = threading.Event()

def work():
    if action == "append":
        write.append(file, ['2024-03-01 * "waited"\\n  Expenses:Food 1.00 USD\\n  Assets:Cash\\n'])
    elif action == "format":
        formatting.format_files([file], in_place=True, prefix_width=None, num_width=None, currency_column=None)
    else:
        with write.lock_files([file, file.with_name("other.bean")]):
            pass
    done.set()

threading.Thread(target=work, daemon=True).start()
os._exit(0 if done.wait(float(sys.argv[3])) else 7)
"""


def _env(tmp_path: Path, cache: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / cache),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return env


def _race(tmp_path: Path, round_: int, *, shared: bool) -> tuple[list[int], str]:
    """Start every writer at once; their exit codes and the ledger they left."""
    books = tmp_path / f"round{round_}"
    books.mkdir()
    ledger = books / "main.bean"
    ledger.write_text(LEDGER)
    children = [
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "cli.main",
                "--file",
                str(ledger),
                "add",
                "transaction",
                f"tx{index}",
                "--date",
                "2024-02-01",
                "-p",
                f"Expenses:Food {index}.00 USD",
                "-p",
                "Assets:Cash",
            ],
            env=_env(books, "cache" if shared else f"cache{index}"),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for index in range(1, WRITERS + 1)
    ]
    try:
        for child in children:
            child.communicate(timeout=300)
    finally:
        for child in children:
            if child.poll() is None:  # pragma: no cover - only on failure
                child.kill()
                child.communicate()
    assert sorted(path.name for path in books.iterdir() if path.name.startswith(".bea-")) == []
    return [child.returncode for child in children], ledger.read_text()


@pytest.mark.parametrize("shared", [False, True], ids=["own-caches", "shared-cache"])
def test_every_concurrent_writer_that_reports_success_is_in_the_ledger(tmp_path: Path, shared: bool) -> None:
    for round_ in range(3):
        codes, text = _race(tmp_path, round_, shared=shared)

        # They queue, as writers on one cache always did: nobody is turned away
        # with a conflict, and nobody's reported write is missing.
        assert codes == [0] * WRITERS
        assert [text.count(f'"tx{index}"') for index in range(1, WRITERS + 1)] == [1] * WRITERS


def _writer(tmp_path: Path, action: str, file: Path, grace: float) -> int:
    return subprocess.run(
        [sys.executable, "-c", WRITER, action, str(file), str(grace)],
        env=_env(tmp_path, "their-cache"),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    ).returncode


@pytest.mark.parametrize("action", ["append", "format", "lock"])
def test_a_writer_with_another_cache_waits_for_the_one_holding_the_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, action: str
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "my-cache"))
    ledger = tmp_path / "main.bean"
    # A three-space indent, so `format` has something to rewrite.
    ledger.write_text(LEDGER + '2024-02-01 * "held"\n   Expenses:Food 1.00 USD\n   Assets:Cash\n')
    before = ledger.read_bytes()

    with write.lock_files([ledger]):
        # Unlocked, each of these finishes in well under a second.
        assert _writer(tmp_path, action, ledger, 3) == 7
        assert ledger.read_bytes() == before

    # Control: the same writer goes straight through once the holder is done.
    assert _writer(tmp_path, action, ledger, 60) == 0
    assert (ledger.read_bytes() == before) is (action == "lock")


def test_files_sharing_a_directory_do_not_make_the_writer_wait_on_itself(tmp_path: Path) -> None:
    """The root ledger and an `--into` file beside it, plus the directory's other spelling."""
    alias = tmp_path / "alias"
    alias.symlink_to(tmp_path, target_is_directory=True)
    files = [tmp_path / "main.bean", tmp_path / "2024.bean", alias / "notes.bean", tmp_path / "missing" / "new.bean"]
    done = threading.Event()

    def lock_all() -> None:
        with write.lock_files(files):
            done.set()

    worker = threading.Thread(target=lock_all, daemon=True)
    worker.start()
    worker.join(timeout=60)

    assert done.is_set(), "a second lock on the same directory blocked its own holder"
    assert write._directory_order(files) == [tmp_path.resolve()]
