"""Tests for the browser device-authorization flow, mocked at the HTTP layer."""

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from pytest_httpx import HTTPXMock

from cli.api.client import make_client
from cli.auth.device_flow import run_device_flow
from cli.errors import AuthError, UnreadableSuccess

DEVICE_CODE = "device-code-kept-in-this-process"
USER_CODE = "BCDF-GHJK"
V1 = "https://api.v3.beancount.io/api-gateway/v1"


def _mock_flow(httpx_mock: HTTPXMock, *statuses: str, expire_at: Any = "2099-01-31T00:00:00.000Z") -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{V1}/cli-sessions",
        json={
            "deviceCode": DEVICE_CODE,
            "userCode": USER_CODE,
            "expiresAt": "2026-01-01T00:10:00.000Z",
            "pollIntervalSeconds": 2,
        },
    )
    for status in statuses:
        httpx_mock.add_response(
            method="GET",
            url=f"{V1}/cli-sessions/{DEVICE_CODE}",
            json={"status": status},
        )
    if statuses and statuses[-1] == "AUTHORIZED":
        httpx_mock.add_response(
            method="POST",
            url=f"{V1}/cli-sessions/{DEVICE_CODE}/consume",
            json={"token": "jwt-token", "expireAt": expire_at},
        )


@pytest.fixture(autouse=True)
def _no_waiting_or_browsing() -> Any:
    with (
        patch("cli.auth.device_flow.time.sleep"),
        patch("cli.auth.device_flow.webbrowser.open") as browser,
        patch("cli.auth.device_flow.save_credentials") as save,
    ):
        yield SimpleNamespace(browser=browser, save=save)


class TestRunDeviceFlow:
    def test_opens_a_verification_url_that_carries_no_secret(
        self, _no_waiting_or_browsing: Any, httpx_mock: HTTPXMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _mock_flow(httpx_mock, "AUTHORIZED")

        run_device_flow(make_client(), "https://beancount.io/")

        opened = _no_waiting_or_browsing.browser.call_args[0][0]
        assert opened == "https://beancount.io/auth/login/device"
        # The device code is this process's private verifier: a URL that carried
        # it would put the credential in history, referrers, and analytics.
        assert DEVICE_CODE not in opened
        assert USER_CODE not in opened

    def test_prints_the_user_code_for_the_person_to_type(
        self, httpx_mock: HTTPXMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _mock_flow(httpx_mock, "AUTHORIZED")

        run_device_flow(make_client(), "https://beancount.io")

        printed = capsys.readouterr().out
        assert USER_CODE in printed
        assert DEVICE_CODE not in printed

    def test_polls_and_redeems_with_the_device_code(self, httpx_mock: HTTPXMock) -> None:
        _mock_flow(httpx_mock, "PENDING", "AUTHORIZED")

        token, expire_at = run_device_flow(make_client(), "https://beancount.io")

        assert token == "jwt-token"
        assert expire_at == "2099-01-31T00:00:00.000Z"
        polls = [r for r in httpx_mock.get_requests() if r.method == "GET"]
        assert [str(r.url) for r in polls] == [f"{V1}/cli-sessions/{DEVICE_CODE}"] * 2
        redemptions = [r for r in httpx_mock.get_requests() if str(r.url).endswith("/consume")]
        assert len(redemptions) == 1

    def test_saves_the_credential_it_was_granted(self, _no_waiting_or_browsing: Any, httpx_mock: HTTPXMock) -> None:
        _mock_flow(httpx_mock, "AUTHORIZED")

        run_device_flow(make_client(), "https://beancount.io")

        _no_waiting_or_browsing.save.assert_called_once_with("jwt-token", "2099-01-31T00:00:00.000Z")

    def test_reports_the_device_it_is_asking_from(self, httpx_mock: HTTPXMock) -> None:
        _mock_flow(httpx_mock, "AUTHORIZED")

        run_device_flow(make_client(), "https://beancount.io")

        create = next(r for r in httpx_mock.get_requests() if str(r.url).endswith("/cli-sessions"))
        reported = json.loads(create.content)["client"]
        assert reported["name"] == "bea"
        assert reported["deviceLabel"]

    def test_raises_when_the_person_denies(self, httpx_mock: HTTPXMock) -> None:
        _mock_flow(httpx_mock, "DENIED")

        with pytest.raises(AuthError, match="denied"):
            run_device_flow(make_client(), "https://beancount.io")

    @pytest.mark.parametrize("status", ["EXPIRED", "CONSUMED"])
    def test_raises_when_the_session_is_no_longer_usable(self, httpx_mock: HTTPXMock, status: str) -> None:
        _mock_flow(httpx_mock, status)

        with pytest.raises(AuthError, match="expired or already used"):
            run_device_flow(make_client(), "https://beancount.io")


class TestUnusableGrants:
    """A grant the next command would refuse is not a login (w5/894)."""

    @pytest.mark.parametrize("expire_at", ["not-a-timestamp", "2099-01-01T00:00:00", 12345, None])
    def test_an_unreadable_expiry_is_an_unexpected_response_and_saves_nothing(
        self, _no_waiting_or_browsing: Any, httpx_mock: HTTPXMock, expire_at: Any
    ) -> None:
        _mock_flow(httpx_mock, "AUTHORIZED", expire_at=expire_at)

        with pytest.raises(UnreadableSuccess, match=r"Unexpected server response \(HTTP 200\)\."):
            run_device_flow(make_client(), "https://beancount.io")

        _no_waiting_or_browsing.save.assert_not_called()

    def test_an_already_expired_grant_is_an_auth_refusal_and_saves_nothing(
        self, _no_waiting_or_browsing: Any, httpx_mock: HTTPXMock
    ) -> None:
        _mock_flow(httpx_mock, "AUTHORIZED", expire_at="2000-01-01T00:00:00Z")

        with pytest.raises(AuthError, match="already expired"):
            run_device_flow(make_client(), "https://beancount.io")

        _no_waiting_or_browsing.save.assert_not_called()
