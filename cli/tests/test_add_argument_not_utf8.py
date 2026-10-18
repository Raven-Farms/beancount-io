"""An `add` argument holding a byte that is not UTF-8 is refused naming the argument (w5/650).

Python hands an undecodable argv byte over as a lone surrogate. It reached
Beancount's parser, which failed with a raw `UnicodeEncodeError … surrogates
not allowed` filed as a validation failure (exit 1).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = "2026-01-01 open Assets:Cash USD\n2026-01-01 open Expenses:Food USD\n"


def _bea(tmp_path: Path, *args: bytes) -> subprocess.CompletedProcess[str]:
    (tmp_path / "main.bean").write_text(LEDGER)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
        LC_ALL="C.UTF-8",
    )
    return subprocess.run(
        [os.fsencode(sys.executable), b"-m", b"cli.main", b"-f", b"main.bean", *args],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
        check=False,
    )


@pytest.mark.parametrize(
    ("args", "label"),
    [
        (
            [b"add", b"transaction", b"caf\xe9", b"--date", b"2026-01-05", b"-p", b"Expenses:Food 1 USD"]
            + [b"-p", b"Assets:Cash"],
            "The narration",
        ),
        ([b"add", b"note", b"-a", b"Assets:Cash", b"-m", b"caf\xe9", b"--date", b"2026-01-05"], "-m/--comment"),
    ],
    ids=["transaction-narration", "note-comment"],
)
def test_a_latin1_byte_is_refused_naming_the_argument(tmp_path: Path, args: list[bytes], label: str) -> None:
    result = _bea(tmp_path, *args)

    assert result.returncode == 2, result.stderr
    assert f"{label} is not valid UTF-8 (byte 0xe9 at position 3); re-type it in a UTF-8 terminal." in result.stderr
    assert "UnicodeEncodeError" not in result.stderr
    assert (tmp_path / "main.bean").read_text() == LEDGER
