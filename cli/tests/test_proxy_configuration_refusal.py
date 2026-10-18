"""Unusable environment proxies name their settings without printing credentials (w5/699)."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDGER = b'option "operating_currency" "USD"\n2026-01-01 open Assets:Cash USD\n'
TOKEN = "synthetic-proxy-token"
PROXY_USER = "proxy-user-w699"
PROXY_PASSWORD = "proxy-pass-w699"
PROXY_HOST = "proxy-host-w699.invalid"
BAD_PROXIES = [
    pytest.param(f"{scheme}://{PROXY_USER}:{PROXY_PASSWORD}@{PROXY_HOST}:45678", id=scheme)
    for scheme in ("socks4", "socks4a", "socks", "ftp", "gopher")
] + [pytest.param(f"http://{PROXY_USER}:{PROXY_PASSWORD}@[::1", id="malformed-ipv6")]


@dataclass
class ProxyStub:
    url: str = ""
    requests: list[tuple[str, str, str | None]] = field(default_factory=list)


@pytest.fixture
def proxy_stub() -> Iterator[ProxyStub]:
    stub = ProxyStub()

    class Handler(BaseHTTPRequestHandler):
        def respond(self) -> None:
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            stub.requests.append((self.command, self.path, self.headers.get("Authorization")))
            endpoint = urlsplit(self.path).path
            if endpoint == "/api-gateway/v1/user-profile":
                payload: object = {
                    "id": 1,
                    "email": "qa@example.invalid",
                    "locale": "en",
                    "username": "proxy-control",
                    "tier": "free",
                    "limits": {
                        "ledgersUsed": 0,
                        "ledgersMax": 1,
                        "collaboratorsPerLedgerMax": 1,
                        "maxDirectives": 100,
                    },
                    "hasEverSubscribed": False,
                }
            elif endpoint == "/api-gateway/ai/openai/chat/completions":
                payload = {
                    "id": "chatcmpl-proxy-control",
                    "object": "chat.completion",
                    "created": 0,
                    "model": "gpt-4o",
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "stop",
                            "message": {"role": "assistant", "content": "Proxy control answer."},
                        }
                    ],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                }
            else:
                assert endpoint == "/api-gateway/v1/ledgers", endpoint
                payload = []
            body = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            self.respond()

        def do_POST(self) -> None:  # noqa: N802
            self.respond()

        def log_message(self, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    stub.url = f"http://127.0.0.1:{server.server_port}"
    worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    worker.start()
    try:
        yield stub
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
        assert not worker.is_alive()


def _env(tmp_path: Path, api_url: str, proxy: dict[str, str]) -> dict[str, str]:
    (tmp_path / "main.bean").write_bytes(LEDGER)
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BEA_")
        and not key.lower().endswith("_proxy")
        and key not in {"CI", "BEANCOUNT_LOAD_CACHE_FILENAME"}
    }
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        XDG_DATA_HOME=str(tmp_path / "data"),
        BEA_NO_UPDATE_NOTIFIER="1",
        BEA_API_URL=api_url,
        BEA_TOKEN=TOKEN,
        PYTHONPATH=str(ROOT / "src"),
        TERM="dumb",
        NO_COLOR="1",
        **proxy,
    )
    return env


def _bea(tmp_path: Path, env: dict[str, str], surface: str, *, debug: bool = False) -> subprocess.CompletedProcess[str]:
    args = ["--debug"] if debug else []
    if surface == "ledger":
        args += ["--json", "cloud", "ledger", "list"]
    elif surface == "status":
        args += ["cloud", "status"]
    else:
        assert surface == "ask"
        args += ["--file", "main.bean", "ask", "--print", "Say hello."]
    return subprocess.run(
        [sys.executable, "-m", "cli.main", "--no-input", *args],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _refusal(done: subprocess.CompletedProcess[str], surface: str, names: set[str]) -> str:
    shown = done.stdout + done.stderr
    assert done.returncode == 2, shown
    if surface == "ledger":
        assert done.stdout == ""
        error = json.loads(done.stderr)["error"]
        assert error["category"] == "usage"
        message = error["message"]
    else:
        message = " ".join(shown.split())
    for name in names:
        assert name in message, message
    for leaked in (PROXY_USER, PROXY_PASSWORD, PROXY_HOST, "45678", "[::1", TOKEN, "pip install"):
        assert leaked not in shown, shown
    assert "Unknown scheme" not in shown
    assert "InvalidURL" not in shown
    assert "ValueError:" not in shown
    assert "Unset" in message and "HTTP(S)" in message
    return message


@pytest.mark.parametrize("proxy", BAD_PROXIES)
@pytest.mark.parametrize("surface", ["ledger", "status", "ask"])
def test_unusable_proxy_urls_are_usage_errors_without_values_even_in_debug(
    tmp_path: Path, proxy_stub: ProxyStub, proxy: str, surface: str
) -> None:
    name = "HTTPS_PROXY" if proxy.startswith("http:") else "ALL_PROXY"
    env = _env(tmp_path, proxy_stub.url, {name: proxy, "NO_PROXY": "127.0.0.1,localhost"})

    done = _bea(tmp_path, env, surface, debug=surface != "status")

    _refusal(done, surface, {name})
    assert proxy_stub.requests == []
    assert (tmp_path / "main.bean").read_bytes() == LEDGER


@pytest.mark.parametrize(
    ("surface", "proxies"),
    [
        ("ask", {"All_Proxy": "socks5://proxy-user-w699:proxy-pass-w699@proxy-host-w699.invalid:45678"}),
        (
            "ledger",
            {
                "ALL_PROXY": "socks5://proxy-user-w699:proxy-pass-w699@proxy-host-w699.invalid:45678",
                "all_proxy": "socks4://proxy-user-w699:proxy-pass-w699@proxy-host-w699.invalid:45678",
            },
        ),
        (
            "status",
            {
                "hTtPs_PrOxY": "ftp://proxy-user-w699:proxy-pass-w699@proxy-host-w699.invalid:45678",
                "Http_Proxy": "socks://proxy-user-w699:proxy-pass-w699@proxy-host-w699.invalid:45678",
            },
        ),
        (
            "ledger",
            {
                "ALL_PROXY": "socks5://proxy-user-w699:proxy-pass-w699@proxy-host-w699.invalid:45678",
                "HTTPS_PROXY": "ftp://proxy-user-w699:proxy-pass-w699@proxy-host-w699.invalid:45678",
            },
        ),
    ],
    ids=["mixed-case", "duplicate-spellings", "multiple-proxy-kinds", "ftp-and-socks"],
)
def test_the_printed_remedy_clears_every_actual_bad_variable_and_allows_a_request(
    tmp_path: Path, proxy_stub: ProxyStub, surface: str, proxies: dict[str, str]
) -> None:
    env = _env(tmp_path, proxy_stub.url, proxies)
    refused = _bea(tmp_path, env, surface, debug=True)
    message = _refusal(refused, surface, set(proxies))
    assert proxy_stub.requests == []
    if len(proxies) > 1:
        assert " name " in message and "Unset them" in message, message
    else:
        assert "All_Proxy names" in message and "ALL_PROXY" not in message, message
    example = re.search(r"for example (.*?) bea …", message)
    assert example is not None, message
    assignments = dict(item.split("=", 1) for item in shlex.split(example.group(1)))
    assert assignments == dict.fromkeys(proxies, ""), message

    # Apply exactly the printed environment assignments, rather than silently
    # deleting all proxy variables and missing an incomplete clearing remedy.
    cleared = _bea(tmp_path, env | assignments, surface)

    assert cleared.returncode == 0, cleared.stdout + cleared.stderr
    assert len(proxy_stub.requests) == 1, proxy_stub.requests
    assert proxy_stub.requests[0][2] == f"Bearer {TOKEN}"
    assert (tmp_path / "main.bean").read_bytes() == LEDGER


@pytest.mark.parametrize("surface", ["ledger", "status", "ask"])
@pytest.mark.parametrize("route", ["http-proxy", "no-proxy-star"])
def test_usable_http_proxies_and_no_proxy_bypasses_still_reach_the_server(
    tmp_path: Path, proxy_stub: ProxyStub, surface: str, route: str
) -> None:
    if route == "http-proxy":
        env = _env(tmp_path, "http://proxy-target-w699.invalid", {"HTTP_PROXY": proxy_stub.url})
    else:
        env = _env(
            tmp_path,
            proxy_stub.url,
            {"HTTP_PROXY": "http://127.0.0.1:9", "ALL_PROXY": "ftp://ignored-proxy.invalid", "No_PrOxY": "*"},
        )

    done = _bea(tmp_path, env, surface)

    assert done.returncode == 0, done.stdout + done.stderr
    assert len(proxy_stub.requests) == 1, proxy_stub.requests
    assert proxy_stub.requests[0][1].startswith("http://proxy-target-w699.invalid/") == (route == "http-proxy")
    assert proxy_stub.requests[0][2] == f"Bearer {TOKEN}"
    if surface == "ledger":
        assert json.loads(done.stdout)["data"] == []
    elif surface == "status":
        assert "proxy-control" in done.stdout
    else:
        assert "Proxy control answer." in done.stdout
    assert (tmp_path / "main.bean").read_bytes() == LEDGER


@pytest.mark.parametrize(
    "failure",
    [
        ImportError("unrelated optional module"),
        ValueError("invalid model setting"),
        httpx.InvalidURL("invalid API URL"),
    ],
    ids=["import", "value", "url"],
)
@pytest.mark.parametrize("valid_proxy", [False, True])
def test_unrelated_client_construction_errors_are_not_misclassified(
    monkeypatch: pytest.MonkeyPatch, failure: Exception, valid_proxy: bool
) -> None:
    from cli.errors import proxy_refusal

    for name in tuple(os.environ):
        if name.lower().endswith("_proxy"):
            monkeypatch.delenv(name)
    if valid_proxy:
        monkeypatch.setenv("HTTP_PROXY", "http://proxy.example.invalid:8080")
    monkeypatch.setenv("NO_PROXY", "socks://this-is-an-exclusion-not-a-proxy")

    assert proxy_refusal(failure) is None


@pytest.mark.parametrize("bypass", ["shadowed", "no-proxy-star"])
def test_ineffective_bad_proxy_settings_do_not_explain_an_unrelated_failure(
    monkeypatch: pytest.MonkeyPatch, bypass: str
) -> None:
    from cli.errors import proxy_refusal

    for name in tuple(os.environ):
        if name.lower().endswith("_proxy"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("HTTP_PROXY", "ftp://proxy-user-w699:proxy-pass-w699@proxy-host-w699.invalid:45678")
    if bypass == "shadowed":
        monkeypatch.setenv("http_proxy", "http://proxy.example.invalid:8080")
    else:
        monkeypatch.setenv("NO_PROXY", "*")

    assert proxy_refusal(ValueError("invalid model setting")) is None
