"""Unresolvable user-home paths are named usage errors on both sides of the engine boundary (w5/695)."""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = 'include "member.bean"\n2026-01-01 open Assets:Checking USD\n2026-01-01 open Expenses:Uncategorized USD\n'
CSV = "Date,Description,Amount\n2026-09-01,Coffee,-5.00\n"


@pytest.fixture
def unknown_user() -> str:
    name = f"bea-no-such-user-w695-{uuid.uuid4().hex}"
    if os.name == "posix":
        import pwd

        with pytest.raises(KeyError):
            pwd.getpwnam(name)
    with pytest.raises(RuntimeError):
        Path(f"~{name}/books.bean").expanduser()
    return name


def _books(tmp_path: Path) -> dict[str, str]:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "member.bean").write_text("")
    (tmp_path / "statement.csv").write_text(CSV)
    (tmp_path / "home").mkdir()
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_") and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    env.update(
        HOME=str(tmp_path / "home"),
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
    return env


def _run(
    tmp_path: Path,
    env: dict[str, str],
    args: list[str],
    *,
    as_json: bool = True,
    engine: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "bea_engine" if engine else "cli.main",
            *([] if engine else [*(["--json"] if as_json else []), "--no-input"]),
            *args,
        ],
        env=env,
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _assert_usage(done: subprocess.CompletedProcess[str], *, as_json: bool, bad: str, source: str) -> None:
    assert done.returncode == 2, done.stdout + done.stderr
    assert done.stdout == ""
    if as_json:
        error = json.loads(done.stderr)["error"]
        assert error["category"] == "usage" and error["exit_code"] == 2
        message = error["message"]
        assert "traceback" not in error
    else:
        message = " ".join(done.stderr.split())
    assert "Cannot expand" in message and "path" in message and source in message
    assert bad in message and "could not determine home directory" in message
    assert "Use ~/, a valid ~user, or an explicit path." in message
    assert "RuntimeError" not in message and "Traceback" not in done.stderr


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
@pytest.mark.parametrize(
    ("case", "source"),
    [
        ("init", "init"),
        ("global-init", "--file"),
        ("environment-ledger", "$BEA_FILE"),
        ("global-ledger", "--file"),
        ("import-source", "import"),
        ("format", "format"),
        ("into", "--into"),
        ("rules", "--rules"),
        ("config", "--config"),
        ("output", "--output"),
        ("config-directory", "BEA_CONFIG_DIR"),
    ],
)
def test_public_paths_name_unresolvable_home_and_source_without_changing_the_books(
    tmp_path: Path, unknown_user: str, case: str, source: str, as_json: bool
) -> None:
    env = _books(tmp_path)
    bad = f"~{unknown_user}/new-parent/books.bean"
    root = ["--file", str(tmp_path / "main.bean")]
    importing = [*root, "import", "statement.csv", "--account", "Assets:Checking"]
    if case == "init":
        args = ["init", bad, "--currency", "USD", "--date", "2026-01-01"]
    elif case == "global-init":
        args = ["--file", bad, "init", "--currency", "USD", "--date", "2026-01-01"]
    elif case == "environment-ledger":
        env["BEA_FILE"] = bad
        args = ["check"]
    elif case == "global-ledger":
        args = ["--file", bad, "check"]
    elif case == "import-source":
        args = [*root, "import", bad, "--account", "Assets:Checking"]
    elif case == "format":
        args = ["format", "--check", bad]
    elif case == "into":
        args = [*root, "add", "open", "--account", "Assets:New", "--date", "2026-01-01", "--into", bad]
    elif case == "rules":
        args = [*importing, "--rules", bad]
    elif case == "config":
        args = [*importing, "--config", bad]
    elif case == "output":
        args = [*root, "query", "PRINT", "--output", bad]
    else:
        env["BEA_CONFIG_DIR"] = bad
        args = ["cloud", "ledger", "list"]
    before = {path: path.read_bytes() for path in (tmp_path / "main.bean", tmp_path / "member.bean")}

    done = _run(tmp_path, env, args, as_json=as_json)

    _assert_usage(done, as_json=as_json, bad=bad, source=source)
    assert {path: path.read_bytes() for path in before} == before
    assert not (tmp_path / f"~{unknown_user}").exists()


def test_the_engine_into_path_is_itself_a_trusted_usage_refusal(tmp_path: Path, unknown_user: str) -> None:
    env = _books(tmp_path)
    bad = f"~{unknown_user}/new-parent/member.bean"
    request = {"date": "2026-01-01", "account": "Assets:New"}
    before = {path: path.read_bytes() for path in (tmp_path / "main.bean", tmp_path / "member.bean")}

    done = _run(
        tmp_path,
        env,
        ["add", "--file", "main.bean", "--type", "open", "--request", json.dumps(request), "--into", bad],
        engine=True,
    )

    assert done.returncode == 2, done.stdout + done.stderr
    error = json.loads(done.stdout)["error"]
    assert error["category"] == "usage" and error["exit_code"] == 2
    assert f"Cannot expand --into path {bad!r}" in error["message"]
    assert "RuntimeError" not in error["message"] and "traceback" not in error
    assert done.stderr == ""
    assert {path: path.read_bytes() for path in before} == before
    assert not (tmp_path / f"~{unknown_user}").exists()


@pytest.mark.parametrize("module", ["cli.paths", "bea_engine.paths"])
@pytest.mark.parametrize("kind", ["relative", "absolute", "home", "known-user"])
def test_path_helpers_preserve_valid_expansion_and_relative_path_semantics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, module: str, kind: str
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "synthetic-home"))
    if kind == "relative":
        given = expected = Path("relative/books.bean")
    elif kind == "absolute":
        given = expected = tmp_path / "absolute.bean"
    elif kind == "home":
        given, expected = Path("~/books.bean"), tmp_path / "synthetic-home" / "books.bean"
    else:
        if os.name != "posix":
            pytest.skip("known-user expansion uses the POSIX account database")
        import pwd

        user = pwd.getpwuid(os.getuid())
        given, expected = Path(f"~{user.pw_name}/books.bean"), Path(user.pw_dir) / "books.bean"

    actual = importlib.import_module(module).expand_path(given, "--file")

    assert actual == expected
    assert actual.is_absolute() == expected.is_absolute()


@pytest.mark.parametrize("module", ["cli.paths", "bea_engine.paths"])
def test_path_helpers_translate_home_runtime_errors_to_their_own_usage_class(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, module: str
) -> None:
    error_type = importlib.import_module("cli.errors" if module == "cli.paths" else "bea_engine.protocol").UsageError
    expand_path = importlib.import_module(module).expand_path
    path = Path("relative source with spaces")

    def unavailable(_path: Path) -> Path:
        raise RuntimeError("synthetic internal home lookup diagnostic")

    monkeypatch.setattr(Path, "expanduser", unavailable)
    with pytest.raises(error_type) as raised:
        expand_path(path, "--config")

    assert raised.value.exit_code == 2
    assert str(raised.value) == (
        f"Cannot expand --config path {str(path)!r}: could not determine home directory. "
        "Use ~/, a valid ~user, or an explicit path."
    )
    assert "synthetic internal" not in str(raised.value)
    assert not (tmp_path / path).exists()


@pytest.mark.parametrize("case", ["init", "environment-ledger", "import", "format", "into"])
def test_valid_current_home_paths_still_work_in_real_commands(tmp_path: Path, case: str) -> None:
    env = _books(tmp_path)
    home = tmp_path / "home"
    root = ["--file", str(tmp_path / "main.bean")]
    before = (tmp_path / "main.bean").read_bytes()
    if case == "init":
        args = ["init", "~/new books/custom.bean", "--currency", "USD", "--date", "2026-01-01"]
    elif case == "environment-ledger":
        (home / "existing.bean").write_text("2026-01-01 open Assets:Other USD\n")
        env["BEA_FILE"] = "~/existing.bean"
        args = ["check"]
    elif case == "import":
        (home / "statement.csv").write_text(CSV)
        args = [*root, "import", "~/statement.csv", "--account", "Assets:Checking"]
    elif case == "format":
        (home / "format.bean").write_text("2026-01-01 open Assets:Other USD\n")
        args = ["format", "--check", "~/format.bean"]
    else:
        (home / "member.bean").write_text("")
        (tmp_path / "main.bean").write_text(LEDGER + f"include {json.dumps(str(home / 'member.bean'))}\n")
        before = (tmp_path / "main.bean").read_bytes()
        args = [*root, "add", "open", "--account", "Assets:New", "--date", "2026-01-01", "--into", "~/member.bean"]

    done = _run(tmp_path, env, args)

    assert done.returncode == 0, done.stdout + done.stderr
    data: dict[str, Any] = json.loads(done.stdout)["data"]
    if case == "init":
        created = home / "new books" / "custom.bean"
        assert created.is_file() and data["created"] == str(created)
        checked = _run(tmp_path, env, ["--file", "~/new books/custom.bean", "check"])
        assert checked.returncode == 0, checked.stdout + checked.stderr
    elif case == "import":
        assert data["ready"] == 1 and data["written"] == 0
    elif case == "into":
        assert "open Assets:New" in (home / "member.bean").read_text()
        assert (tmp_path / "member.bean").read_text() == ""
    assert (tmp_path / "main.bean").read_bytes() == before
