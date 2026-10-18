"""Init distinguishes a directory supplied as --file from an occupied ledger file (w5/694)."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _bea(tmp_path: Path, *args: str, as_json: bool = True) -> subprocess.CompletedProcess[str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_") and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_UPDATE_API_URL="http://127.0.0.1:9",
        BEA_TAP_FORMULA_URL="http://127.0.0.1:9/bea.rb",
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, "-m", "cli.main", *(["--json"] if as_json else []), "--no-input", *args],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _message(done: subprocess.CompletedProcess[str], *, as_json: bool, code: int) -> str:
    assert done.returncode == code, done.stdout + done.stderr
    assert done.stdout == ""
    if as_json:
        error = json.loads(done.stderr)["error"]
        assert error["category"] == ("usage" if code == 2 else "conflict")
        assert error["exit_code"] == code
        return str(error["message"])
    return " ".join(done.stderr.split())


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
@pytest.mark.parametrize("symlink", [False, True], ids=["directory", "directory-symlink"])
@pytest.mark.parametrize("given_currency", [False, True], ids=["before-currency-prompt", "explicit-currency"])
def test_a_global_file_directory_is_usage_with_both_shell_quoted_remedies(
    tmp_path: Path, as_json: bool, symlink: bool, given_currency: bool
) -> None:
    directory = tmp_path / "my books' directory"
    directory.mkdir()
    target = tmp_path / "linked books' directory" if symlink else directory
    if symlink:
        target.symlink_to(directory, target_is_directory=True)
    before = list(directory.iterdir())

    done = _bea(
        tmp_path,
        "--file",
        target.name,
        "init",
        *(["--currency", "USD", "--date", "2026-08-01"] if given_currency else []),
        as_json=as_json,
    )

    message = _message(done, as_json=as_json, code=2)
    assert "is a directory" in message and "expected a ledger file" in message
    assert str(target) in message
    assert shlex.join(["bea", "init", str(target)]) in message
    assert f"--file {shlex.quote(str(target / 'main.bean'))}" in message
    assert "Choose an operating currency" not in message
    assert "never overwrites a ledger" not in message
    assert list(directory.iterdir()) == before
    assert not (directory / "main.bean").exists()
    if symlink:
        assert target.is_symlink() and target.readlink() == directory


@pytest.mark.parametrize("suffix", [".bean", ".beancount"])
@pytest.mark.parametrize("symlink", [False, True], ids=["directory", "directory-symlink"])
def test_both_directory_remedies_work_even_when_the_directory_name_has_a_ledger_suffix(
    tmp_path: Path, suffix: str, symlink: bool
) -> None:
    directory = tmp_path / f"my books' directory{suffix}"
    directory.mkdir()
    target = tmp_path / f"linked books' directory{suffix}" if symlink else directory
    if symlink:
        target.symlink_to(directory, target_is_directory=True)

    refused = _bea(tmp_path, "--file", target.name, "init")
    message = _message(refused, as_json=True, code=2)

    assert list(directory.iterdir()) == []
    positional = message.partition("Use ")[2].partition(" for a directory target")[0]
    explicit_file = message.partition(", or ")[2].partition(" for a file target")[0]
    assert shlex.split(positional) == ["bea", "init", str(target)]
    assert shlex.split(explicit_file) == ["--file", str(target / "main.bean")]
    ledger = target / "main.bean"
    for arguments in (shlex.split(positional)[1:], [*shlex.split(explicit_file), "init"]):
        created = _bea(tmp_path, *arguments, "--currency", "USD", "--date", "2026-08-01")
        assert created.returncode == 0, created.stdout + created.stderr
        assert ledger.is_file()
        checked = _bea(tmp_path, "--file", str(ledger), "check")
        assert checked.returncode == 0, checked.stdout + checked.stderr
        assert json.loads(checked.stdout)["data"]["valid"] is True
        ledger.unlink()
    assert list(directory.iterdir()) == []
    if symlink:
        assert target.is_symlink() and target.readlink() == directory


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
@pytest.mark.parametrize("dangling", [False, True], ids=["existing-file", "dangling-link"])
def test_an_occupied_global_file_keeps_the_conflict_contract_before_prompting(
    tmp_path: Path, as_json: bool, dangling: bool
) -> None:
    target = tmp_path / "existing.bean"
    if dangling:
        target.symlink_to("missing-target.bean")
    else:
        target.write_bytes(b"preserve existing ledger bytes\n")

    done = _bea(tmp_path, "--file", target.name, "init", as_json=as_json)

    message = _message(done, as_json=as_json, code=4)
    assert "Already exists" in message and "init never overwrites a ledger" in message
    assert "is a directory" not in message
    if dangling:
        assert target.is_symlink() and target.readlink() == Path("missing-target.bean")
        assert not (tmp_path / "missing-target.bean").exists()
    else:
        assert target.read_bytes() == b"preserve existing ledger bytes\n"


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_a_positional_existing_empty_directory_still_creates_its_main_ledger(tmp_path: Path, as_json: bool) -> None:
    directory = tmp_path / "my books' directory"
    directory.mkdir()

    done = _bea(tmp_path, "init", str(directory), "--currency", "USD", "--date", "2026-08-01", as_json=as_json)

    assert done.returncode == 0, done.stdout + done.stderr
    ledger = directory / "main.bean"
    assert ledger.is_file() and list(directory.iterdir()) == [ledger]
    checked = _bea(tmp_path, "--file", str(ledger), "check")
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert json.loads(checked.stdout)["data"]["valid"] is True


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_a_missing_explicit_global_file_still_creates_that_file_and_its_parents(tmp_path: Path, as_json: bool) -> None:
    ledger = tmp_path / "new books' directory" / "custom.bean"

    done = _bea(
        tmp_path,
        "--file",
        str(ledger),
        "init",
        "--currency",
        "USD",
        "--date",
        "2026-08-01",
        as_json=as_json,
    )

    assert done.returncode == 0, done.stdout + done.stderr
    assert ledger.is_file() and list(ledger.parent.iterdir()) == [ledger]
    checked = _bea(tmp_path, "--file", str(ledger), "check")
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert json.loads(checked.stdout)["data"]["valid"] is True
