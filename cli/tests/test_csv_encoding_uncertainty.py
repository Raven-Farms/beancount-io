"""CSV decoding advice admits uncertainty, including when an 8-bit codec is remembered (w5/713)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = (
    'option "operating_currency" "EUR"\n'
    "2026-01-01 open Assets:Checking EUR\n"
    "2026-01-01 open Expenses:Uncategorized EUR\n"
)
MAPPING = "date=Date,narration=Description,amount=Amount"
FOREIGN = [
    pytest.param("Poplatek za vedení účtu", "cp1250", id="czech"),
    pytest.param("東京電力", "shift_jis", id="japanese"),
    pytest.param("Wpłata Łódź", "cp1250", id="polish"),
    pytest.param("Пятёрочка", "cp1251", id="russian"),
    pytest.param("ΔΕΗ", "cp1253", id="greek"),
    pytest.param("İşlem ücreti", "cp1254", id="turkish"),
]
WESTERN = ["Wasser 12m³ Stadtwerke", "McDonald´s Köln", "UK£20", "Þýðing", "Café Crème"]


@pytest.fixture
def root(tmp_path: Path) -> Path:
    path = tmp_path / "main.bean"
    path.write_text(LEDGER)
    return path


def _env(directory: Path) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_") and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    env.update(
        BEA_CONFIG_DIR=str(directory / "config"),
        XDG_CACHE_HOME=str(directory / "cache"),
        XDG_DATA_HOME=str(directory / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return env


def _source(root: Path, name: str, narration: str, codec: str, *, date: str = "2026-03-01") -> Path:
    path = root.parent / name
    path.write_bytes(f"Date,Description,Amount\n{date},{narration},-4.50\n".encode(codec))
    return path


def _import(root: Path, source: Path, *args: str, as_json: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "cli.main",
            *(["--json"] if as_json else []),
            "--no-input",
            "--file",
            str(root),
            "import",
            str(source),
            *args,
        ],
        cwd=root.parent,
        env=_env(root.parent),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _data(done: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    assert done.returncode == 0, done.stdout + done.stderr
    return dict(json.loads(done.stdout)["data"])


def _conditional_advice(done: subprocess.CompletedProcess[str], source: Path, *, as_json: bool) -> None:
    assert done.returncode == 2, done.stdout + done.stderr
    assert done.stdout == ""
    if as_json:
        error = json.loads(done.stderr)["error"]
        assert error["category"] == "usage" and error["exit_code"] == 2
        message = str(error["message"])
    else:
        message = " ".join(done.stderr.split())
    assert source.name in message and "not valid UTF-8" in message
    assert "Re-save the export as UTF-8" in message
    assert "--csv encoding=cp1252 only if" in message
    assert "Western European Windows-1252 (cp1252)" in message
    assert "looks like another code page" not in message
    assert "Read as cp1252 it shows" not in message
    assert "it decodes as cp1252 — pass --csv encoding=cp1252." not in message


@pytest.mark.parametrize("as_json", [False, True], ids=["human-auto", "json-mapped"])
@pytest.mark.parametrize(("narration", "codec"), FOREIGN)
def test_undecidable_non_utf8_exports_always_get_conditional_advice(
    root: Path, narration: str, codec: str, as_json: bool
) -> None:
    source = _source(root, "foreign.csv", narration, codec)
    before = {path: path.read_bytes() for path in (root, source)}

    done = _import(
        root,
        source,
        "--account",
        "Assets:Checking",
        *(["--csv", MAPPING] if as_json else []),
        "--apply",
        as_json=as_json,
    )

    _conditional_advice(done, source, as_json=as_json)
    assert {path: path.read_bytes() for path in before} == before
    assert not list((root.parent / "config" / "importers").glob("csv-*.json"))


@pytest.mark.parametrize("narration", WESTERN)
def test_western_text_keeps_the_conditional_cp1252_hint_without_a_foreign_claim(root: Path, narration: str) -> None:
    source = _source(root, "western.csv", narration, "cp1252")
    before = root.read_bytes()

    done = _import(root, source, "--account", "Assets:Checking", as_json=False)

    _conditional_advice(done, source, as_json=False)
    assert root.read_bytes() == before


def _stored_mapping(root: Path) -> str:
    (record,) = (root.parent / "config" / "importers").glob("csv-*.json")
    (entry,) = json.loads(record.read_text())["sources"]
    return str(entry["mapping"])


def _remember(root: Path, codec: str) -> None:
    source = _source(root, "seed.csv", "Café Crème", codec, date="2026-01-05")
    seeded = _data(
        _import(
            root,
            source,
            "--csv",
            f"{MAPPING},encoding={codec}",
            "--account",
            "Assets:Checking",
            "--apply",
        )
    )
    assert seeded["written"] == 1
    assert not any("may misread" in str(note) for note in seeded.get("notes", []))
    assert f"encoding={codec}" in _stored_mapping(root)


def _notice(source: Path, codec: str) -> str:
    return (
        f"Remembered --csv encoding={codec} may misread {source.name}: non-UTF-8 bytes do not identify "
        "their code page. Re-save the export as UTF-8, or confirm its encoding and pass "
        f"--csv encoding={codec} explicitly. The remembered mapping is unchanged."
    )


@pytest.mark.parametrize("apply", [False, True], ids=["human-preview", "json-apply"])
@pytest.mark.parametrize("narration", ["Wpłata Łódki", "Wasser 12m³ Stadtwerke"], ids=["polish", "western"])
@pytest.mark.parametrize("codec", ["cp1252", "latin-1"])
def test_a_remembered_8bit_codec_warns_for_each_new_non_utf8_file_without_changing_the_codec(
    root: Path, codec: str, narration: str, apply: bool
) -> None:
    _remember(root, codec)
    source_codec = "cp1250" if narration.startswith("Wpłata") else "cp1252"
    source = _source(root, "next.csv", narration, source_codec)
    source_before = source.read_bytes()
    before = root.read_bytes()
    mapping = _stored_mapping(root)

    done = _import(root, source, *(["--apply"] if apply else []), as_json=apply)

    assert done.returncode == 0, done.stdout + done.stderr
    expected = _notice(source, codec)
    if apply:
        data = json.loads(done.stdout)["data"]
        assert data["written"] == 1 and data["config_source"] == "remembered --csv"
        assert expected in data["notes"]
        # A warning permits the explicitly documented legacy decoding; it does
        # not magically determine the real code page or promise to avoid mojibake.
        decoded = narration.encode(source_codec).decode(codec)
        assert decoded in root.read_text()
        assert root.read_bytes().startswith(before)
    else:
        assert expected in " ".join(done.stderr.split())
        assert "1 ready" in done.stdout
        assert root.read_bytes() == before
    assert "looks like another code page" not in done.stdout + done.stderr
    assert _stored_mapping(root) == mapping
    assert source.read_bytes() == source_before


@pytest.mark.parametrize("kind", ["ascii", "utf8"])
@pytest.mark.parametrize("codec", ["cp1252", "latin-1"])
def test_remembered_codecs_stay_quiet_for_ascii_and_yield_to_real_utf8(root: Path, codec: str, kind: str) -> None:
    _remember(root, codec)
    narration = "Plain bank fee" if kind == "ascii" else "Poplatek za vedení účtu 東京電力"
    source = _source(root, "next.csv", narration, "utf-8")
    mapping = _stored_mapping(root)

    data = _data(_import(root, source, "--apply"))

    assert data["written"] == 1 and narration in root.read_text()
    notes = " ".join(str(note) for note in data.get("notes", []))
    assert "may misread" not in notes and "non-UTF-8 bytes do not identify" not in notes
    if kind == "utf8":
        assert f"Remembered --csv encoding={codec} does not match next.csv" in notes
        assert "read it as UTF-8" in notes
    else:
        assert "read it as UTF-8" not in notes
    assert _stored_mapping(root) == mapping


@pytest.mark.parametrize("codec", ["cp1252", "latin-1"])
def test_a_codec_explicitly_confirmed_on_this_run_is_authoritative(root: Path, codec: str) -> None:
    _remember(root, codec)
    narration = "McDonald´s Köln £20"
    source = _source(root, "next.csv", narration, codec)

    data = _data(_import(root, source, "--csv", f"encoding={codec}", "--apply"))

    assert data["written"] == 1 and narration in root.read_text()
    assert not any("may misread" in str(note) for note in data.get("notes", []))
    assert f"encoding={codec}" in _stored_mapping(root)


@pytest.mark.parametrize(
    ("narration", "codec"),
    [("Poplatek za vedení účtu", "cp1250"), ("Wasser 12m³ Stadtwerke", "cp1252")],
    ids=["czech", "western"],
)
def test_engine_header_reads_give_the_same_conditional_encoding_advice(root: Path, narration: str, codec: str) -> None:
    from bea_engine.csv_mapper import read_header
    from bea_engine.protocol import UsageError

    source = _source(root, "engine.csv", narration, codec)
    with pytest.raises(UsageError) as caught:
        read_header(source)

    message = str(caught.value)
    assert "Re-save the export as UTF-8" in message
    assert "--csv encoding=cp1252 only if" in message
    assert "looks like another code page" not in message
