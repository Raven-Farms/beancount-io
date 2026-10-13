"""list note reports a note's tags and links, like list document (w5/171)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """2024-01-01 open Assets:Bank
2024-01-05 note Assets:Bank "called the bank about the fee" #zeta #dispute ^case-17 ^case-02
2024-01-05 document Assets:Bank "receipts/r.pdf" #zeta #dispute ^case-17 ^case-02
2024-01-06 note Assets:Bank "plain"
"""


def _bea(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
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
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _ledger(tmp_path: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    (tmp_path / "receipts").mkdir()
    (tmp_path / "receipts" / "r.pdf").write_bytes(b"%PDF")
    return ledger


def _rows(tmp_path: Path, ledger: Path, kind: str) -> list[dict[str, object]]:
    result = _bea(tmp_path, "--json", "--file", str(ledger), "list", kind)
    assert result.returncode == 0, result.stderr or result.stdout
    rows: list[dict[str, object]] = json.loads(result.stdout)["data"]
    return rows


def test_list_note_json_carries_sorted_tags_and_links(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    tagged, plain = _rows(tmp_path, ledger, "note")
    assert tagged == {
        "date": "2024-01-05",
        "account": "Assets:Bank",
        "comment": "called the bank about the fee",
        "tags": ["dispute", "zeta"],
        "links": ["case-02", "case-17"],
        "meta": {},
    }
    # A note without them is unchanged apart from the two empty fields.
    assert plain == {
        "date": "2024-01-06",
        "account": "Assets:Bank",
        "comment": "plain",
        "tags": [],
        "links": [],
        "meta": {},
    }
    # Control: the same line shape as a document reports the same sets.
    (document,) = _rows(tmp_path, ledger, "document")
    assert (document["tags"], document["links"]) == (tagged["tags"], tagged["links"])


def test_list_note_table_shows_tags_and_links(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    human = _bea(tmp_path, "--file", str(ledger), "list", "note")
    assert human.returncode == 0, human.stderr or human.stdout
    header, _rule, tagged, plain = human.stdout.splitlines()
    assert header.split() == ["DATE", "ACCOUNT", "COMMENT", "TAGS", "LINKS"]
    assert tagged.split()[-4:] == ["#dispute", "#zeta", "^case-02", "^case-17"]
    assert plain.split() == ["2024-01-06", "Assets:Bank", "plain"]
    # Control: the document table renders the same two cells.
    control = _bea(tmp_path, "--file", str(ledger), "list", "document")
    assert control.returncode == 0, control.stderr or control.stdout
    assert control.stdout.splitlines()[2].split()[-4:] == tagged.split()[-4:]
