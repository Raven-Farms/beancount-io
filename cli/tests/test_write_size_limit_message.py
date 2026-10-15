"""A write the filesystem will not take (full disk, size limit) says nothing was written (w5/410).

Only a permission refusal had a sentence; `EFBIG` and `ENOSPC` reached the
user as `OSError: [Errno 27] File too large`, saying nothing about the ledger
or the output being untouched. A file-size limit stands in for a full disk.
"""

from __future__ import annotations

import json
import os
import resource
import signal
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="RLIMIT_FSIZE")


def _limited() -> None:
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    resource.setrlimit(resource.RLIMIT_FSIZE, (4096, 4096))


def _ledger(books: Path) -> str:
    lines = [
        'option "operating_currency" "USD"',
        "2026-01-01 open Assets:Cash USD",
        "2026-01-01 open Expenses:Food USD",
    ]
    for day in range(80):
        lines += [
            f'2026-02-{day % 28 + 1:02d} * "lunch {day} with a long narration"',
            "  Expenses:Food 2 USD",
            "  Assets:Cash",
        ]
    text = "\n".join(lines) + "\n"
    (books / "main.bean").write_text(text)
    return text


def _bea(books: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "-f", str(books / "main.bean"), *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
        preexec_fn=_limited,
    )


@pytest.mark.parametrize("json_output", [False, True])
def test_add_over_the_limit_leaves_the_ledger(tmp_path: Path, json_output: bool) -> None:
    before = _ledger(tmp_path)
    args = ["add", "transaction", "X", "--date", "2026-03-05", "-p", "Expenses:Food 2 USD", "-p", "Assets:Cash"]
    result = _bea(tmp_path, *(["--json"] if json_output else []), *args)

    assert result.returncode == 1, result.stderr
    message = json.loads(result.stderr)["error"]["message"] if json_output else result.stderr
    assert f"Cannot write a staged copy of main.bean in {tmp_path} (File too large); nothing was written." in message
    assert "OSError" not in result.stderr and "Errno" not in result.stderr
    assert (tmp_path / "main.bean").read_text() == before
    assert not [path for path in tmp_path.iterdir() if path.name.startswith(".bea-")]


@pytest.mark.parametrize(
    ("json_output", "sentence"),
    [
        (False, "Cannot write a staged copy of q.csv in {out} (File too large)"),
        (True, "Cannot write {out}/q.csv (File too large)"),
    ],
    ids=["text", "json"],
)
def test_query_output_over_the_limit_writes_nothing(tmp_path: Path, json_output: bool, sentence: str) -> None:
    _ledger(tmp_path)
    out = tmp_path / "o"
    out.mkdir()
    result = _bea(
        tmp_path,
        *(["--json"] if json_output else []),
        "query",
        "SELECT date, account, narration, position",
        "-o",
        str(out / "q.csv"),
    )
    assert result.returncode == 1, result.stderr
    assert sentence.format(out=out) + "; nothing was written." in result.stderr
    assert "Errno" not in result.stderr
    assert list(out.iterdir()) == []
