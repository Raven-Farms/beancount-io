"""Reject HTTP hosts the transport cannot encode before logout removes a credential (w5/700)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from cli.config import settings
from cli.errors import UsageError
from cli.main import app

ROOT = Path(__file__).resolve().parents[1]
BAD_HOSTS = [
    pytest.param("http://xn--qa.example.invalid", id="invalid-punycode"),
    pytest.param("https://api.example.invalid\u200b", id="zero-width-space"),
    pytest.param("https://api.example.invalid\u00a0", id="nonbreaking-space"),
]
VALID_URLS = [
    pytest.param("https://bücher.example.invalid/", id="unicode-idn"),
    pytest.param("https://xn--bcher-kva.example.invalid/", id="punycode-idn"),
    pytest.param("http://[::1]:8080/api", id="ipv6-port-path"),
    pytest.param("http://localhost:8765", id="localhost-port"),
    pytest.param("https://api.example.invalid/custom/prefix/", id="path-prefix"),
]
LEDGER = b'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n'
CREDENTIAL = b'{\n  "token": "synthetic-idna-stored-token",\n  "expireAt": "2099-01-01T00:00:00+00:00"\n}\n'


@pytest.mark.parametrize("variable", ["BEA_API_URL", "BEA_DASHBOARD_URL"])
@pytest.mark.parametrize("value", BAD_HOSTS)
def test_both_endpoint_settings_reject_hosts_httpx_cannot_encode(
    monkeypatch: pytest.MonkeyPatch, variable: str, value: str
) -> None:
    monkeypatch.delenv("BEA_API_URL", raising=False)
    monkeypatch.delenv("BEA_DASHBOARD_URL", raising=False)
    monkeypatch.setenv(variable, value)

    with pytest.raises(UsageError) as caught:
        settings()

    assert caught.value.exit_code == 2
    assert str(caught.value).startswith(f"{variable} must be an http(s) URL with a host")
    assert "IDNA" not in str(caught.value) and "Codepoint" not in str(caught.value)


@pytest.mark.parametrize("variable", ["BEA_API_URL", "BEA_DASHBOARD_URL"])
@pytest.mark.parametrize("value", VALID_URLS)
def test_valid_international_and_local_endpoints_are_kept_without_resolving_them(
    monkeypatch: pytest.MonkeyPatch, variable: str, value: str
) -> None:
    monkeypatch.delenv("BEA_API_URL", raising=False)
    monkeypatch.delenv("BEA_DASHBOARD_URL", raising=False)
    monkeypatch.setenv(variable, value)

    configured = settings()

    selected = configured.api_url if variable == "BEA_API_URL" else configured.dashboard_url
    assert selected == value
    # URL/request construction validates IDNA without doing DNS or making a
    # network request. The stored setting retains the person's spelling.
    request = httpx.Request("GET", selected)
    assert request.url.host and request.url.scheme in {"http", "https"}


def _env(tmp_path: Path, api_url: str) -> dict[str, str]:
    (tmp_path / "main.bean").write_bytes(LEDGER)
    credential = tmp_path / "config" / "credentials.json"
    credential.parent.mkdir()
    credential.write_bytes(CREDENTIAL)
    credential.chmod(0o600)
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_")
        and not key.lower().endswith("_proxy")
        and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    env.update(
        BEA_CONFIG_DIR=str(credential.parent),
        BEA_API_URL=api_url,
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_UPDATE_API_URL="http://127.0.0.1:9",
        BEA_TAP_FORMULA_URL="http://127.0.0.1:9/bea.rb",
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
        TERM="dumb",
    )
    return env


def _bea(tmp_path: Path, env: dict[str, str], args: list[str], *, as_json: bool) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", *(["--json"] if as_json else []), *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _assert_usage_and_unchanged(tmp_path: Path, done: subprocess.CompletedProcess[str], *, as_json: bool) -> None:
    assert done.returncode == 2, done.stdout + done.stderr
    assert done.stdout == ""
    if as_json:
        error = json.loads(done.stderr)["error"]
        assert error["category"] == "usage" and error["exit_code"] == 2
        message = error["message"]
    else:
        message = " ".join(done.stderr.split())
    assert "BEA_API_URL must be an http(s) URL with a host" in message
    for misleading in (
        "Codepoint",
        "Invalid IDNA",
        "Traceback",
        "Could not reach",
        "Removed the local credential",
        "server revocation failed",
        "synthetic-idna-stored-token",
    ):
        assert misleading not in done.stderr
    assert (tmp_path / "config" / "credentials.json").read_bytes() == CREDENTIAL
    assert (tmp_path / "main.bean").read_bytes() == LEDGER


@pytest.mark.parametrize("value", BAD_HOSTS)
@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_logout_refuses_invalid_idna_before_removing_the_stored_credential(
    tmp_path: Path, value: str, as_json: bool
) -> None:
    env = _env(tmp_path, value)

    done = _bea(tmp_path, env, ["cloud", "logout"], as_json=as_json)

    _assert_usage_and_unchanged(tmp_path, done, as_json=as_json)


@pytest.mark.parametrize("value", BAD_HOSTS)
@pytest.mark.parametrize("command", ["ledger", "status"])
def test_other_cloud_commands_use_the_same_host_validation(tmp_path: Path, value: str, command: str) -> None:
    env = _env(tmp_path, value)
    env["BEA_TOKEN"] = "synthetic-idna-environment-token"
    args = ["cloud", "ledger", "list"] if command == "ledger" else ["cloud", "status"]

    done = _bea(tmp_path, env, args, as_json=command == "ledger")

    _assert_usage_and_unchanged(tmp_path, done, as_json=command == "ledger")


def test_ask_refuses_the_same_host_before_constructing_its_model_client(tmp_path: Path) -> None:
    env = _env(tmp_path, "https://api.example.invalid\u200b")

    done = _bea(tmp_path, env, ["--file", "main.bean", "ask", "--print", "Hello."], as_json=False)

    _assert_usage_and_unchanged(tmp_path, done, as_json=False)


@pytest.mark.parametrize("as_json", [False, True], ids=["human", "json"])
def test_logout_keeps_the_credential_if_request_building_raises_before_transport(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, as_json: bool
) -> None:
    env = _env(tmp_path, "http://127.0.0.1:9")
    for name in tuple(os.environ):
        if name.startswith("BEA_") or name.lower().endswith("_proxy"):
            monkeypatch.delenv(name)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    built = 0

    def fail_build(self: httpx.Client, *args: object, **kwargs: object) -> httpx.Request:
        nonlocal built
        built += 1
        raise ValueError("synthetic request construction failure")

    monkeypatch.setattr(httpx.Client, "build_request", fail_build)

    done = CliRunner().invoke(app, [*(["--json"] if as_json else []), "cloud", "logout"])

    assert done.exit_code == 1, done.output
    assert done.stdout == "" and built == 1
    if as_json:
        error = json.loads(done.stderr)["error"]
        assert error["category"] == "validation" and error["exit_code"] == 1
    assert "synthetic request construction failure" in done.stderr
    assert "Removed the local credential" not in done.stderr
    assert "server revocation failed" not in done.stderr
    assert (tmp_path / "config" / "credentials.json").read_bytes() == CREDENTIAL
    assert (tmp_path / "main.bean").read_bytes() == LEDGER
