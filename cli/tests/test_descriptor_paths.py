"""Descriptor paths either pass through or are refused by name, and are never remembered (w5/792).

`--rules /dev/stdin < r.toml` worked once but stored `/dev/fd/0`: the next
plain import replayed the dead descriptor (dropping the rules, or waiting on
a terminal). A `/dev/fd/N` that names a regular file passed the w5/582 pipe
check and then failed in the engine child with "not found" or "Permission
denied". Now a held `--rules` descriptor passes through (`pass_fds`, or the
inherited stdin for descriptor 0) and applies to that run only; `--config`,
the import source, `-f`, `--source`, format targets and doctor operands are
refused by name, since the child cannot open them (`runpy` opens twice on
one shared offset; the export is read through one shared offset by both
sides; a ledger needs a stable path).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from cli.paths import descriptor_number, held_descriptor, is_descriptor_path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = """option "operating_currency" "USD"
2026-01-01 open Assets:Checking USD
2026-01-01 open Expenses:Food USD
2026-01-01 open Expenses:Uncategorized USD
"""
EXPORT = "Date,Payee,Amount\n2026-01-07,Cafe Nero,-3.00\n"
RULES = '[[rule]]\nmatch = "cafe"\naccount = "Expenses:Food"\n'
OTHER_RULES = '[[rule]]\nmatch = "nero"\naccount = "Expenses:Food"\n'
CSV_FLAGS = ["--csv", "date=Date,payee=Payee,amount=Amount", "--account", "Assets:Checking"]

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="/dev/fd names")


@pytest.fixture
def books(tmp_path: Path) -> Path:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "s.csv").write_text(EXPORT)
    (tmp_path / "r.toml").write_text(RULES)
    (tmp_path / "r2.toml").write_text(OTHER_RULES)
    return tmp_path


def _bea(
    books: Path,
    *args: str,
    stdin_data: str | None = None,
    stdin_file: Path | None = None,
    pass_fds: tuple[int, ...] = (),
) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        XDG_DATA_HOME=str(books / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    handle = open(stdin_file, "rb") if stdin_file is not None else None
    try:
        return subprocess.run(
            [sys.executable, "-m", "cli.main", "--no-input", *args],
            env=env,
            cwd=books,
            capture_output=True,
            text=True,
            timeout=120,
            input=stdin_data,
            stdin=handle if handle is not None else (None if stdin_data is not None else subprocess.DEVNULL),
            pass_fds=pass_fds,
        )
    finally:
        if handle is not None:
            handle.close()


def _csv_record(books: Path) -> dict:
    matches = list((books / "config" / "importers").glob("csv-*.json"))
    assert len(matches) == 1
    return json.loads(matches[0].read_text())


def test_descriptor_spellings() -> None:
    assert descriptor_number("/dev/stdin") == 0
    assert descriptor_number("/dev/fd/3") == 3
    assert descriptor_number("/dev/fd/0") == 0
    assert descriptor_number("/proc/self/fd/7") == 7
    assert descriptor_number("main.bean") is None
    assert descriptor_number("/dev/fd/x") is None
    assert descriptor_number("/dev/stdout") is None
    assert is_descriptor_path("/dev/fd/3")
    assert not is_descriptor_path("r.toml")


def test_held_descriptor_needs_an_open_fd(tmp_path: Path) -> None:
    assert held_descriptor("/dev/stdin") in (0, None)
    target = tmp_path / "x"
    target.write_text("x")
    fd = os.open(target, os.O_RDONLY)
    try:
        assert held_descriptor(f"/dev/fd/{fd}") == fd
    finally:
        os.close(fd)
    assert held_descriptor(f"/dev/fd/{fd}") is None


@pytest.mark.parametrize("redirect", ["pipe", "regular"], ids=["pipe-stdin", "regular-stdin"])
def test_rules_stdin_applies_once_and_is_not_remembered(books: Path, redirect: str) -> None:
    if redirect == "pipe":
        result = _bea(
            books, "-f", "main.bean", "import", "s.csv", *CSV_FLAGS, "--rules", "/dev/stdin", stdin_data=RULES
        )
    else:
        result = _bea(
            books,
            "-f",
            "main.bean",
            "import",
            "s.csv",
            *CSV_FLAGS,
            "--rules",
            "/dev/stdin",
            stdin_file=books / "r.toml",
        )

    assert result.returncode == 0, result.stderr
    assert "Expenses:Food" in result.stdout
    assert "applies to this import only and is not remembered" in result.stderr
    assert _csv_record(books)["sources"][0]["rules"] is None

    rerun = _bea(books, "-f", "main.bean", "import", "s.csv")
    assert rerun.returncode == 0, rerun.stderr
    assert "unmatched" in rerun.stdout
    assert "cannot be used" not in rerun.stderr
    assert "file descriptor" not in rerun.stderr


def test_rules_regular_fd_passes_through_unremembered(books: Path) -> None:
    fd = os.open(books / "r.toml", os.O_RDONLY)
    try:
        result = _bea(
            books, "-f", "main.bean", "import", "s.csv", *CSV_FLAGS, "--rules", f"/dev/fd/{fd}", pass_fds=(fd,)
        )
    finally:
        os.close(fd)

    assert result.returncode == 0, result.stderr
    assert "Expenses:Food" in result.stdout
    assert "applies to this import only and is not remembered" in result.stderr
    assert _csv_record(books)["sources"][0]["rules"] is None


def test_rules_dead_fd_is_refused_by_name(books: Path) -> None:
    result = _bea(books, "-f", "main.bean", "import", "s.csv", *CSV_FLAGS, "--rules", "/dev/fd/9")

    assert result.returncode == 2, result.stdout + result.stderr
    assert "--rules /dev/fd/9 is a file descriptor this process does not hold open." in result.stderr.replace("\n", "")
    assert "Traceback" not in result.stderr


def test_config_descriptor_is_refused(books: Path) -> None:
    fd = os.open(books / "r.toml", os.O_RDONLY)
    try:
        result = _bea(books, "-f", "main.bean", "import", "s.csv", "--config", f"/dev/fd/{fd}", pass_fds=(fd,))
    finally:
        os.close(fd)

    assert result.returncode == 2, result.stdout + result.stderr
    assert f"--config /dev/fd/{fd} is a file descriptor, not a file." in result.stderr.replace("\n", "")


def test_remembered_rules_descriptor_is_dropped_without_opening(books: Path) -> None:
    seed = _bea(books, "-f", "main.bean", "import", "s.csv", *CSV_FLAGS, "--rules", "r.toml")
    assert seed.returncode == 0, seed.stderr
    record = next((books / "config" / "importers").glob("csv-*.json"))
    data = json.loads(record.read_text())
    data["sources"][0]["rules"] = "/dev/fd/0"
    record.write_text(json.dumps(data))

    # stdin even holds usable rules: opening the descriptor would apply them.
    result = _bea(books, "-f", "main.bean", "import", "s.csv", stdin_data=RULES)

    assert result.returncode == 0, result.stderr
    assert "Remembered --rules /dev/fd/0 names a file descriptor, not a file" in result.stderr.replace("\n", "")
    assert "unmatched" in result.stdout
    assert _csv_record(books)["sources"][0]["rules"] is None


def test_descriptor_run_keeps_the_prior_rules_memory(books: Path) -> None:
    first = _bea(books, "-f", "main.bean", "import", "s.csv", *CSV_FLAGS, "--rules", "r.toml")
    assert first.returncode == 0, first.stderr
    assert "cafe" in first.stdout

    # The descriptor run uses its own rules (match `nero`), not the memory.
    second = _bea(
        books, "-f", "main.bean", "import", "s.csv", *CSV_FLAGS, "--rules", "/dev/stdin", stdin_data=OTHER_RULES
    )
    assert second.returncode == 0, second.stderr
    assert "nero" in second.stdout
    assert "applies to this import only" in second.stderr

    # The next plain run replays the remembered rules (match `cafe`).
    third = _bea(books, "-f", "main.bean", "import", "s.csv")
    assert third.returncode == 0, third.stderr
    assert "cafe" in third.stdout
    assert "nero" not in third.stdout
    assert _csv_record(books)["sources"][0]["rules"] is not None


def test_remembered_config_descriptor_is_ignored(books: Path) -> None:
    (books / "cfg.py").write_text(
        "import datetime\n"
        "from decimal import Decimal as D\n"
        "from beancount.core import amount, data\n"
        "class Cafe:\n"
        "    name = 'cafe'\n"
        "    def identify(self, filepath):\n"
        "        with open(filepath) as f:\n"
        '            return f.readline().strip() == "Date,Payee,Amount"\n'
        "    def account(self, filepath):\n"
        '        return "Assets:Checking"\n'
        "    def extract(self, filepath, existing):\n"
        "        legs = [data.Posting(a, amount.Amount(D(n), 'USD'), None, None, None, None)\n"
        '                for a, n in (("Assets:Checking", "-3.00"), ("Expenses:Food", "3.00"))]\n'
        '        meta = data.new_metadata("s.csv", 1)\n'
        '        return [data.Transaction(meta, datetime.date(2026, 1, 7), "*", None, "r",\n'
        "                                data.EMPTY_SET, data.EMPTY_SET, legs)]\n"
        "CONFIG = [Cafe()]\n"
    )
    seed = _bea(books, "-f", "main.bean", "import", "s.csv", "--config", "cfg.py")
    assert seed.returncode == 0, seed.stderr
    record = next(p for p in (books / "config" / "importers").glob("*.json") if not p.name.startswith("csv-"))
    data = json.loads(record.read_text())
    data["config"] = "/dev/fd/9"
    record.write_text(json.dumps(data))
    (books / "weird.dat").write_text("not a header at all\n(((((\n")

    result = _bea(books, "-f", "main.bean", "import", "weird.dat")

    assert result.returncode == 2, result.stdout + result.stderr
    assert "Choose a Python importer with --config FILE" in result.stderr.replace("\n", "")
    assert "names a file descriptor, not a file; ignoring it" in result.stderr.replace("\n", "")


def test_import_source_descriptor_is_refused(books: Path) -> None:
    fd = os.open(books / "s.csv", os.O_RDONLY)
    try:
        result = _bea(books, "-f", "main.bean", "import", f"/dev/fd/{fd}", *CSV_FLAGS, pass_fds=(fd,))
    finally:
        os.close(fd)

    assert result.returncode == 2, result.stdout + result.stderr
    assert f"Export /dev/fd/{fd} is a file descriptor, not a file." in result.stderr.replace("\n", "")


def test_ledger_descriptor_is_refused(books: Path) -> None:
    fd = os.open(books / "main.bean", os.O_RDONLY)
    try:
        result = _bea(books, "-f", f"/dev/fd/{fd}", "check", pass_fds=(fd,))
    finally:
        os.close(fd)

    assert result.returncode == 2, result.stdout + result.stderr
    assert f"Ledger path '/dev/fd/{fd}' (from --file) is a file descriptor, not a file." in result.stderr.replace(
        "\n", ""
    )


@pytest.mark.parametrize("spelling", ["descriptor", "uri"], ids=["bare", "uri"])
def test_query_source_descriptor_is_refused(books: Path, spelling: str) -> None:
    fd = os.open(books / "main.bean", os.O_RDONLY)
    try:
        source = f"/dev/fd/{fd}" if spelling == "descriptor" else f"beancount:/dev/fd/{fd}"
        result = _bea(books, "query", "--source", source, "SELECT 1;", pass_fds=(fd,))
    finally:
        os.close(fd)

    assert result.returncode == 2, result.stdout + result.stderr
    assert "is a file descriptor, not a file" in result.stderr.replace("\n", "")


def test_engine_refuses_the_descriptor_source_itself(books: Path) -> None:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_")}
    env.update(
        BEA_CONFIG_DIR=str(books / "config"),
        XDG_CACHE_HOME=str(books / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    fd = os.open(books / "main.bean", os.O_RDONLY)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "bea_engine", "source-query", "--format", "csv", f"/dev/fd/{fd}", "SELECT 1;"],
            env=env,
            cwd=books,
            capture_output=True,
            text=True,
            timeout=120,
            stdin=subprocess.DEVNULL,
            pass_fds=(fd,),
        )
    finally:
        os.close(fd)

    assert result.returncode == 2, result.stdout + result.stderr
    assert "is a file descriptor, not a file" in result.stderr.replace("\n", "")


def test_format_target_descriptor_is_refused(books: Path) -> None:
    fd = os.open(books / "main.bean", os.O_RDONLY)
    try:
        result = _bea(books, "format", "--check", f"/dev/fd/{fd}", pass_fds=(fd,))
    finally:
        os.close(fd)

    assert result.returncode == 2, result.stdout + result.stderr
    assert f"Formatting target /dev/fd/{fd} is a file descriptor, not a file." in result.stderr.replace("\n", "")


def test_doctor_operand_descriptor_is_refused(books: Path) -> None:
    fd = os.open(books / "main.bean", os.O_RDONLY)
    try:
        result = _bea(books, "doctor", "lex", f"/dev/fd/{fd}", pass_fds=(fd,))
    finally:
        os.close(fd)

    assert result.returncode == 2, result.stdout + result.stderr
    assert f"Ledger path /dev/fd/{fd} is a file descriptor, not a file." in result.stderr.replace("\n", "")
