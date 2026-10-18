"""Offline guards run before cloud requests, quote tools, upgrades and first-use installs (w5/689)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from cli import context
from cli.api import client
from cli.engine import provision
from cli.errors import UsageError

ROOT = Path(__file__).resolve().parents[1]
LEDGER = "2026-01-01 open Assets:Cash USD\n"


@pytest.fixture
def server() -> Iterator[tuple[str, list[tuple[str, str, bytes]]]]:
    seen: list[tuple[str, str, bytes]] = []

    class Handler(BaseHTTPRequestHandler):
        def answer(self) -> None:
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            seen.append((self.command, self.path, body))
            if self.path.endswith("/pypi/beancount-io/json"):
                payload: object = {"info": {"version": "9.9.9"}}
            elif self.command == "POST":
                request = json.loads(body)
                payload = {
                    "id": "synthetic-ledger",
                    "name": request["name"],
                    "fullName": f"synthetic/{request['name']}",
                    "sshUrl": "ssh://git@example.invalid/synthetic/newbook.git",
                    "httpUrl": "https://example.invalid/synthetic/newbook.git",
                    "empty": True,
                    "private": True,
                    "createdAt": "2026-01-01T00:00:00Z",
                    "updatedAt": "2026-01-01T00:00:00Z",
                    "size": 0,
                    "description": request.get("description"),
                }
            else:
                payload = {"ok": True, "data": {"items": [], "total": 0}}
            encoded = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        do_GET = do_POST = do_DELETE = answer  # noqa: N815 - upstream handler names

        def log_message(self, *args: Any) -> None:
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}", seen
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def _environment(directory: Path, *, site: str = "", **updates: str) -> dict[str, str]:
    (directory / "main.bean").write_text(LEDGER)
    binary = directory / "bin"
    binary.mkdir(exist_ok=True)
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_") and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    env.update(
        BEA_CONFIG_DIR=str(directory / "config"),
        XDG_CACHE_HOME=str(directory / "cache"),
        XDG_DATA_HOME=str(directory / "data"),
        BEA_ENGINE_DIR=str(directory / "managed" / "engine"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_UPDATE_API_URL="http://127.0.0.1:9",
        BEA_TAP_FORMULA_URL="http://127.0.0.1:9/bea.rb",
        BEA_TOKEN="synthetic-offline-token",
        PYTHONPATH=str(ROOT / "src"),
        PATH=os.pathsep.join([str(binary), os.environ["PATH"]]),
        TERM="dumb",
        NO_COLOR="1",
    )
    if site:
        bootstrap = directory / "bootstrap"
        bootstrap.mkdir(exist_ok=True)
        (bootstrap / "sitecustomize.py").write_text(site)
        env["PYTHONPATH"] = os.pathsep.join([str(bootstrap), env["PYTHONPATH"]])
    return env | updates


def _run(
    directory: Path, env: dict[str, str], *args: str, as_json: bool = False, offline: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "cli.main",
            *(["--json"] if as_json else []),
            *(["--offline"] if offline else []),
            *args,
        ],
        cwd=directory,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _refused(done: subprocess.CompletedProcess[str], *, as_json: bool, command: str) -> None:
    assert done.returncode == 2, done.stdout + done.stderr
    assert done.stdout == ""
    if as_json:
        error = json.loads(done.stderr)["error"]
        assert error["category"] == "usage" and error["exit_code"] == 2
        message = error["message"]
    else:
        message = done.stderr
    assert f"{command} requires network access" in message, message
    assert "remove --offline" in message, message


def _program(directory: Path, name: str, *, output: str = "", status: int = 0) -> Path:
    binary = directory / "bin" / name
    binary.parent.mkdir(exist_ok=True)
    binary.write_text(
        f"#!{sys.executable}\nimport json, sys\nfrom pathlib import Path\n"
        f"with Path({str(directory / 'executed.jsonl')!r}).open('a') as out:\n"
        "    out.write(json.dumps([Path(sys.argv[0]).name, *sys.argv[1:]]) + '\\n')\n"
        f"print({output!r}, end='')\nraise SystemExit({status})\n"
    )
    binary.chmod(0o755)
    return binary


def _engine(directory: Path, *, managed: bool = False) -> Path:
    root = directory / "managed" / "engine" if managed else directory / "fake-engine"
    binary = root / "bin" / "python"
    binary.parent.mkdir(parents=True)
    binary.write_text(
        f"#!{sys.executable}\nimport json, os, sys\nfrom pathlib import Path\n"
        f"with Path({str(directory / 'engine.jsonl')!r}).open('a') as out:\n"
        "    out.write(json.dumps(sys.argv[1:]) + '\\n')\n"
        "if sys.argv[1:3] == ['-P', '-c'] and 'bea-packages-imported' in sys.argv[3]:\n"
        "    print('bea-packages-imported')\n"
        "else:\n"
        f"    os.execv({sys.executable!r}, [{sys.executable!r}, *sys.argv[1:]])\n"
    )
    binary.chmod(0o755)
    for package in ("beancount", "beanquery"):
        (root / "lib" / "python3.12" / "site-packages" / package).mkdir(parents=True)
    quote = _program(directory, "bean-price", output="2026-01-02 price AAPL 10 USD\n")
    (binary.parent / "bean-price").symlink_to(quote)
    return binary


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
@pytest.mark.parametrize(
    "tail",
    [
        ["newbook", "-d", "-h"],
        ["newbook", "-d", "--help"],
        ["--", "-h"],
        ["--", "--help"],
    ],
    ids=["short-help-description", "long-help-description", "short-help-name", "long-help-name"],
)
def test_help_tokens_used_as_cloud_values_never_disable_offline(
    tmp_path: Path, server: tuple[str, list[tuple[str, str, bytes]]], as_json: bool, tail: list[str]
) -> None:
    origin, seen = server
    env = _environment(tmp_path, BEA_API_URL=origin)

    done = _run(tmp_path, env, "cloud", "ledger", "create", *tail, as_json=as_json)

    _refused(done, as_json=as_json, command="bea cloud")
    assert seen == []


@pytest.mark.parametrize("tail", [["newbook", "-d", "-h"], ["--", "-h"]], ids=["description", "name"])
def test_help_token_values_without_offline_are_sent_to_the_cloud_stub(
    tmp_path: Path, server: tuple[str, list[tuple[str, str, bytes]]], tail: list[str]
) -> None:
    origin, seen = server
    env = _environment(tmp_path, BEA_API_URL=origin)

    done = _run(tmp_path, env, "cloud", "ledger", "create", *tail, as_json=True, offline=False)

    assert done.returncode == 0, done.stdout + done.stderr
    assert len(seen) == 1 and seen[0][:2] == ("POST", "/api-gateway/v1/ledgers")
    request = json.loads(seen[0][2])
    assert request["description"] == "-h" if tail[0] == "newbook" else request["name"] == "-h"


@pytest.mark.parametrize("args", [["cloud"], ["cloud", "ledger"], ["cloud", "ledger", "create"], ["cloud", "login"]])
def test_genuine_cloud_help_still_answers_offline_without_credentials(
    tmp_path: Path, server: tuple[str, list[tuple[str, str, bytes]]], args: list[str]
) -> None:
    origin, seen = server
    env = _environment(tmp_path, BEA_API_URL=origin)
    env.pop("BEA_TOKEN")

    done = _run(tmp_path, env, *args, "--help")

    assert done.returncode == 0 and "Usage:" in done.stdout, done.stdout + done.stderr
    assert "requires network access" not in done.stdout + done.stderr
    assert seen == []


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
@pytest.mark.parametrize("command", ["login", "logout", "status"])
def test_cloud_account_commands_refuse_before_reading_or_removing_a_bad_credential(
    tmp_path: Path, server: tuple[str, list[tuple[str, str, bytes]]], command: str, as_json: bool
) -> None:
    origin, seen = server
    env = _environment(tmp_path, BEA_API_URL=origin)
    env.pop("BEA_TOKEN")
    credential = tmp_path / "config" / "credentials.json"
    credential.parent.mkdir()
    credential.write_bytes(b"this malformed synthetic credential must remain untouched\n")
    before = credential.read_bytes()

    done = _run(tmp_path, env, "cloud", command, as_json=as_json)

    _refused(done, as_json=as_json, command=f"bea cloud {command}")
    assert seen == [] and credential.read_bytes() == before


def test_generated_cloud_commands_refuse_before_the_missing_login_error(tmp_path: Path) -> None:
    env = _environment(tmp_path)
    env.pop("BEA_TOKEN")

    done = _run(tmp_path, env, "cloud", "ledger", "list", as_json=True)

    _refused(done, as_json=True, command="bea cloud")
    assert "Not logged in" not in done.stderr


@pytest.mark.parametrize("kind", ["anonymous", "bearer", "authenticated"])
def test_all_cloud_client_entrypoints_enforce_offline_before_settings_or_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    monkeypatch.setattr(context, "_context", context.RunContext(offline=True))
    monkeypatch.setenv("BEA_API_URL", "not-an-http-url")
    monkeypatch.setenv("BEA_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("BEA_TOKEN", raising=False)
    credential = tmp_path / "credentials.json"
    credential.write_text("not JSON\n")

    with pytest.raises(UsageError, match="bea cloud requires network access; remove --offline"):
        if kind == "anonymous":
            client.make_client()
        elif kind == "bearer":
            client.bearer_client("synthetic-offline-token")
        else:
            client.authenticated_client()

    assert credential.read_text() == "not JSON\n"


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
@pytest.mark.parametrize("source", ["expression", "ledger"])
def test_forwarded_price_refuses_before_probing_or_running_beanprice(
    tmp_path: Path, source: str, as_json: bool
) -> None:
    python = _engine(tmp_path)
    env = _environment(tmp_path, BEA_ENGINE_PYTHON=str(python))
    args = ["-e", "USD:yahoo/AAPL"] if source == "expression" else [str(tmp_path / "main.bean")]

    done = _run(tmp_path, env, "price", *args, as_json=as_json)

    _refused(done, as_json=as_json, command="bea price")
    assert not (tmp_path / "engine.jsonl").exists()
    assert not (tmp_path / "executed.jsonl").exists()
    assert (tmp_path / "main.bean").read_text() == LEDGER


def test_forwarded_price_without_offline_reaches_the_quote_shim(tmp_path: Path) -> None:
    python = _engine(tmp_path)
    env = _environment(tmp_path, BEA_ENGINE_PYTHON=str(python))

    done = _run(tmp_path, env, "price", "-e", "USD:yahoo/AAPL", offline=False)

    assert done.returncode == 0, done.stdout + done.stderr
    assert "price AAPL 10 USD" in done.stdout
    assert json.loads((tmp_path / "executed.jsonl").read_text()) == ["bean-price", "-e", "USD:yahoo/AAPL"]


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
@pytest.mark.parametrize("feature", ["beanprice", "beangulp"])
def test_engine_enable_refuses_before_creating_an_engine_or_running_uv(
    tmp_path: Path, feature: str, as_json: bool
) -> None:
    uv = _program(tmp_path, "uv", status=73)
    env = _environment(tmp_path, BEA_UV=str(uv))

    done = _run(tmp_path, env, "engine", "enable", feature, as_json=as_json)

    _refused(done, as_json=as_json, command="bea engine enable")
    assert not (tmp_path / "managed").exists()
    assert not (tmp_path / "executed.jsonl").exists()


def test_offline_engine_enable_refuses_even_when_the_feature_was_already_enabled(tmp_path: Path) -> None:
    python = _engine(tmp_path, managed=True)
    metadata = python.parent.parent / "bea-features.json"
    metadata.write_text(json.dumps({"enabled": ["beanprice"]}))
    before = metadata.read_bytes()
    uv = _program(tmp_path, "uv", status=73)
    env = _environment(tmp_path, BEA_UV=str(uv))

    done = _run(tmp_path, env, "engine", "enable", "beanprice", as_json=True)

    _refused(done, as_json=True, command="bea engine enable")
    assert metadata.read_bytes() == before
    assert not (tmp_path / "engine.jsonl").exists()
    assert not (tmp_path / "executed.jsonl").exists()
    assert not python.parent.parent.with_name("engine.lock").exists()


@pytest.mark.parametrize("channel", ["HOMEBREW", "UV_TOOL", "PIPX"])
def test_upgrade_refuses_before_any_package_manager_process(tmp_path: Path, channel: str) -> None:
    for name in ("brew", "uv", "pipx"):
        _program(tmp_path, name)
    env = _environment(
        tmp_path, site=f"from cli.commands import upgrade\nupgrade.current_channel = lambda: upgrade.{channel}\n"
    )

    done = _run(tmp_path, env, "upgrade", as_json=True)

    _refused(done, as_json=True, command="bea upgrade")
    assert not (tmp_path / "executed.jsonl").exists()


def test_online_upgrade_still_executes_the_selected_manager(tmp_path: Path) -> None:
    _program(tmp_path, "brew")
    env = _environment(
        tmp_path, site="from cli.commands import upgrade\nupgrade.current_channel = lambda: upgrade.HOMEBREW\n"
    )

    done = _run(tmp_path, env, "upgrade", as_json=True, offline=False)

    assert done.returncode == 0, done.stdout + done.stderr
    assert json.loads(done.stdout)["data"]["ran"] is True
    assert json.loads((tmp_path / "executed.jsonl").read_text()) == ["brew", "upgrade", "bea"]


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_explicit_upgrade_check_keeps_its_documented_offline_exception(
    tmp_path: Path, server: tuple[str, list[tuple[str, str, bytes]]], as_json: bool
) -> None:
    origin, seen = server
    _program(tmp_path, "uv")
    env = _environment(
        tmp_path,
        site="from cli.commands import upgrade\nupgrade.current_channel = lambda: upgrade.UV_TOOL\n",
        BEA_UPDATE_API_URL=origin,
    )

    done = _run(tmp_path, env, "upgrade", "--check", as_json=as_json)

    assert done.returncode == 0, done.stdout + done.stderr
    assert "9.9.9" in done.stdout
    assert [path for method, path, _ in seen if method == "GET"] == ["/pypi/beancount-io/json"]
    assert not (tmp_path / "executed.jsonl").exists()


INSTALLED_CONTEXT = (
    "from pathlib import Path\nfrom cli.engine import paths\n"
    "paths.checkout_source_root = lambda: None\n"
    f"paths.helper_source_root = lambda: Path({str(ROOT / 'src')!r})\n"
)


@pytest.mark.parametrize("state", ["missing", "incomplete"])
@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_first_use_offline_refuses_without_lock_build_or_partial_directory(
    tmp_path: Path, state: str, as_json: bool
) -> None:
    uv = _program(tmp_path, "uv", status=73)
    env = _environment(tmp_path, site=INSTALLED_CONTEXT, BEA_UV=str(uv))
    engine = Path(env["BEA_ENGINE_DIR"])
    if state == "incomplete":
        engine.mkdir(parents=True)
        (engine / ".bea-engine").write_text("synthetic incomplete engine\n")
        (engine / "keep.txt").write_text("keep\n")
    before = {path.relative_to(engine): path.read_bytes() for path in engine.rglob("*") if path.is_file()}

    done = _run(tmp_path, env, "--file", str(tmp_path / "main.bean"), "check", as_json=as_json)

    assert done.returncode == 2, done.stdout + done.stderr
    assert "--offline" in done.stderr and "engine" in done.stderr.lower()
    assert "Installing the Beancount engine" not in done.stderr
    assert not (tmp_path / "executed.jsonl").exists()
    assert not engine.with_name("engine.lock").exists()
    assert not list(engine.parent.glob("engine.partial.*"))
    assert {path.relative_to(engine): path.read_bytes() for path in engine.rglob("*") if path.is_file()} == before
    if state == "missing":
        assert not engine.parent.exists()


def test_offline_reuses_a_ready_managed_engine_without_uv(tmp_path: Path) -> None:
    _engine(tmp_path, managed=True)
    uv = _program(tmp_path, "uv", status=73)
    env = _environment(tmp_path, site=INSTALLED_CONTEXT, BEA_UV=str(uv))

    done = _run(tmp_path, env, "--file", str(tmp_path / "main.bean"), "list", "open", as_json=True)

    assert done.returncode == 0, done.stdout + done.stderr
    assert "Assets:Cash" in done.stdout
    assert (tmp_path / "engine.jsonl").is_file()
    assert not (tmp_path / "executed.jsonl").exists()
    assert not (tmp_path / "managed" / "engine.lock").exists()


def test_offline_reuses_an_existing_interpreter_override_without_provisioning(tmp_path: Path) -> None:
    uv = _program(tmp_path, "uv", status=73)
    env = _environment(tmp_path, BEA_ENGINE_PYTHON=sys.executable, BEA_UV=str(uv))

    done = _run(tmp_path, env, "--file", str(tmp_path / "main.bean"), "list", "open", as_json=True)

    assert done.returncode == 0, done.stdout + done.stderr
    assert "Assets:Cash" in done.stdout
    assert not (tmp_path / "executed.jsonl").exists()
    assert not (tmp_path / "managed").exists()


@pytest.mark.parametrize("entry", ["ensure", "provision", "enable"])
def test_direct_provisioning_entrypoints_respect_offline_before_building(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entry: str
) -> None:
    monkeypatch.setattr(context, "_context", context.RunContext(offline=True))
    monkeypatch.delenv("BEA_ENGINE_PYTHON", raising=False)
    engine = tmp_path / "new-parent" / "engine"
    monkeypatch.setenv("BEA_ENGINE_DIR", str(engine))
    uv = _program(tmp_path, "uv", status=73)
    monkeypatch.setenv("BEA_UV", str(uv))

    with pytest.raises(UsageError, match="--offline"):
        if entry == "ensure":
            provision.ensure_engine()
        elif entry == "enable":
            provision.enable_feature("beanprice")
        else:
            provision.provision(engine)

    assert not engine.parent.exists()
    assert not (tmp_path / "executed.jsonl").exists()
