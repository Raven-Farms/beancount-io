"""Doctor operations that load the ledger refuse one it cannot decode (w5/440).

Upstream logs the parser's `UnicodeDecodeError` and carries on: `missing-open`
and `context` exited 0 with nothing to say, which read as "nothing missing",
and `print-options` relayed the class name. `check` names the file, the byte
and the fix (w5/278); doctor now does too.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = (
    b'option "operating_currency" "USD"\n'
    b"2026-01-01 open Assets:Cash USD\n"
    b"2026-01-01 open Expenses:Food USD\n"
    b'2026-01-09 * "caf\xe9"\n'
    b"  Expenses:Food 5 USD\n"
    b"  Assets:Cash\n"
)


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
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=books,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.parametrize(
    "op",
    [["missing-open"], ["print-options"], ["roundtrip"], ["context", "4"], ["display-context"], ["directories"]],
    ids=lambda op: op[0],
)
def test_a_loading_operation_names_the_byte_and_the_remedy(tmp_path: Path, op: list[str]) -> None:
    main = tmp_path / "main.bean"
    main.write_bytes(LEDGER)
    checked = _bea(tmp_path, "-f", str(main), "check")
    message = (
        f"Cannot decode '{main}' as UTF-8: invalid continuation byte at byte 117. Re-save the file as UTF-8 and retry."
    )
    assert checked.returncode == 1 and message in checked.stderr, checked.stderr

    result = _bea(tmp_path, "doctor", op[0], str(main), *op[1:])

    assert result.returncode == 1, result.stderr
    assert f"Error: {message}\n" in result.stderr
    assert "UnicodeDecodeError" not in result.stderr


def test_an_included_file_is_named_and_a_comment_byte_still_loads(tmp_path: Path) -> None:
    (tmp_path / "bad.bean").write_bytes(LEDGER)
    (tmp_path / "main.bean").write_text('option "operating_currency" "USD"\ninclude "bad.bean"\n')
    included = _bea(tmp_path, "doctor", "missing-open", str(tmp_path / "main.bean"))
    assert included.returncode == 1
    assert f"Cannot decode '{tmp_path / 'bad.bean'}' as UTF-8" in included.stderr

    (tmp_path / "comment.bean").write_bytes(
        b'option "operating_currency" "USD"\n; caf\xe9\n2026-01-01 open Assets:Cash USD\n'
    )
    commented = _bea(tmp_path, "doctor", "missing-open", str(tmp_path / "comment.bean"))
    assert commented.returncode == 0, commented.stderr
