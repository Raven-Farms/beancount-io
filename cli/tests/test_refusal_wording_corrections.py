"""Four refusal messages say the wrong thing (w5/738).

Each case already refused with the right exit code and wrote nothing; only
the message misled: decode offsets skipped a leading BOM, a stray NUL was
called UTF-16, `--from ''` advised omitting a required option, and a
non-string tagged metadata value leaked raw `TypeError` text.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "title" "T"
2026-01-01 open Expenses:Food USD
2026-01-01 open Assets:Cash USD
"""
ROW = (
    '{"date":"2026-02-01","narration":"n","postings":['
    '{"account":"Expenses:Food","amount":"1 USD"},{"account":"Assets:Cash","amount":"-1 USD"}]}'
)
BOM = b"\xef\xbb\xbf"


def _bea(tmp_path: Path, *args: str, stdin: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    (tmp_path / "main.bean").write_text(LEDGER)
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *args],
        env=env,
        cwd=tmp_path,
        input=stdin,
        capture_output=True,
        timeout=120,
    )


def test_bom_decode_offset_is_raw(tmp_path: Path) -> None:
    bad = BOM + b'[{"date":"2026-02-01","narration":"caf\xe9"}]'
    (tmp_path / "bombad.json").write_bytes(bad)

    result = _bea(tmp_path, "-f", "main.bean", "add", "transactions", "--from", "bombad.json")

    assert result.returncode == 2, result.stderr
    assert f"invalid continuation byte at byte {bad.index(0xE9)}." in result.stderr.decode()


def test_bom_decode_offset_is_raw_on_stdin(tmp_path: Path) -> None:
    query = BOM + "SELECT 'caf\xe9'\n".encode("latin-1")
    queried = _bea(tmp_path, "-f", "main.bean", "query", stdin=query)
    assert queried.returncode == 2, queried.stderr
    assert f"at byte {query.index(0xE9)}." in queried.stderr.decode()

    ledger = BOM + "2026-01-01 open A\xe9\n".encode("latin-1")
    formatted = _bea(tmp_path, "format", "-", stdin=ledger)
    assert formatted.returncode == 1, formatted.stderr
    assert f"at byte {ledger.index(0xE9)}." in formatted.stderr.decode()


def test_a_stray_nul_names_its_offset_not_utf16(tmp_path: Path) -> None:
    rows = (f"[{ROW}]").encode() + b"\x00"
    (tmp_path / "nul.json").write_bytes(rows)

    result = _bea(tmp_path, "-f", "main.bean", "add", "transactions", "--from", "nul.json")

    assert result.returncode == 2, result.stderr
    message = result.stderr.decode()
    assert "UTF-16" not in message
    assert f"contains a NUL byte at byte {rows.index(0)}; remove it and retry." in message


def test_alternating_nuls_are_still_utf16(tmp_path: Path) -> None:
    (tmp_path / "le.json").write_bytes(f"[{ROW}]".encode("utf-16-le"))

    result = _bea(tmp_path, "-f", "main.bean", "add", "transactions", "--from", "le.json")

    assert result.returncode == 2, result.stderr
    assert "looks like UTF-16" in result.stderr.decode()


def test_utf32_names_its_nul(tmp_path: Path) -> None:
    rows = f"[{ROW}]".encode("utf-32-le")
    (tmp_path / "u32.json").write_bytes(rows)

    result = _bea(tmp_path, "-f", "main.bean", "add", "transactions", "--from", "u32.json")

    assert result.returncode == 2, result.stderr
    message = result.stderr.decode()
    assert "UTF-16" not in message
    assert f"contains a NUL byte at byte {rows.index(0)};" in message


def test_an_empty_required_option_does_not_advise_omitting_it(tmp_path: Path) -> None:
    result = _bea(tmp_path, "-f", "main.bean", "add", "transactions", "--from", "")

    assert result.returncode == 2, result.stderr
    message = result.stderr.decode()
    assert "--from '' is empty; name a path." in message
    assert "omit" not in message


def test_an_empty_optional_option_still_advises_omitting_it(tmp_path: Path) -> None:
    result = _bea(
        tmp_path,
        "-f",
        "main.bean",
        "add",
        "transaction",
        "x",
        "--date",
        "2026-01-08",
        "-p",
        "Expenses:Food 1 USD",
        "-p",
        "Assets:Cash",
        "--into",
        "",
    )

    assert result.returncode == 2, result.stderr
    assert "--into '' is empty; name a path, or omit --into." in result.stderr.decode()


def test_a_non_string_tagged_value_must_be_a_string(tmp_path: Path) -> None:
    dated = (
        '[{"date":"2026-02-01","narration":"n","meta":{"td":{"kind":"date","value":20260201}},'
        '"postings":[{"account":"Expenses:Food","amount":"1 USD"},{"account":"Assets:Cash","amount":"-1 USD"}]}]'
    )
    (tmp_path / "tag.json").write_text(dated)
    result = _bea(tmp_path, "-f", "main.bean", "add", "transactions", "--from", "tag.json")

    assert result.returncode == 1, result.stderr
    message = result.stderr.decode()
    assert "Invalid 'date' metadata for 'td': expected a 'YYYY-MM-DD' string." in message
    assert "bytes-like" not in message

    nulled = (
        '[{"date":"2026-02-01","narration":"n","meta":{"nn":{"kind":"number","value":null}},'
        '"postings":[{"account":"Expenses:Food","amount":"1 USD"},{"account":"Assets:Cash","amount":"-1 USD"}]}]'
    )
    (tmp_path / "tagnull.json").write_text(nulled)
    result = _bea(tmp_path, "-f", "main.bean", "add", "transactions", "--from", "tagnull.json")

    assert result.returncode == 1, result.stderr
    message = result.stderr.decode()
    assert "Invalid 'number' metadata for 'nn': expected a decimal string such as '1.25'." in message
    assert "NoneType" not in message
