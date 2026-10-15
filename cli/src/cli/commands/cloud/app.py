"""The `bea cloud` namespace: every command that talks to the hosted service.

Account commands (login/logout/status) sit directly on the app — the cloud
surface is too small for an `auth` sub-level — and hosted resources mount as
sub-apps (`cloud ledger`). Task verbs never live here: a local verb that gains
remote capability grows a target option, it does not move.
"""

from __future__ import annotations

import typer

from cli import context, output
from cli.commands.cloud.ledger.app import ledger_app

cloud_app = typer.Typer(
    help="Hosted ledgers and AI proxy; see 'cloud login'.",
    no_args_is_help=True,
    rich_markup_mode=None,
)
cloud_app.add_typer(ledger_app, name="ledger")


@cloud_app.command("login")
def cloud_login() -> None:
    """Log in via the browser device flow (stores credentials.json under $BEA_CONFIG_DIR, default ~/.config/bea)."""
    ctx = context.current()
    if ctx.no_input:
        from cli.errors import UsageError

        raise UsageError("Login needs a browser and a terminal. Set BEA_TOKEN for unattended use.")

    from cli.api.client import make_client
    from cli.auth.device_flow import run_device_flow
    from cli.config import settings

    run_device_flow(make_client(), settings().dashboard_url)
    output.success("Logged in successfully.")


@cloud_app.command("logout")
def cloud_logout() -> None:
    """Revoke the token and clear stored credentials."""
    from cli.api.client import bearer_client, call, unwrap_or_none
    from cli.api.rest_client.api.ledger_v_1 import logout
    from cli.auth.credentials import ENVIRONMENT, UnusableCredentials, clear_credentials, load_credentials
    from cli.errors import BeaError

    try:
        creds = load_credentials()
    except UnusableCredentials as exc:
        # Without a readable token nothing can be revoked, but the file still
        # holds whatever it holds: remove it, and do not call that a logout.
        try:
            clear_credentials()
        except OSError as error:
            raise BeaError(f"{exc} It could not be removed either: {error.strerror}.") from error
        raise BeaError(
            f"Removed the unusable credential file {exc.path}; it could not be revoked. "
            "If it held a live session, revoke it from the dashboard."
        ) from exc
    if creds is None:
        output.success("Already logged out.")
        return
    if creds.source == ENVIRONMENT:
        # `BEA_TOKEN` is the shared, unattended credential: a CI job or a
        # teammate may be using the same value right now. Revoking it from a
        # routine logout would silently kill every other consumer, and this
        # process cannot unset the caller's shell anyway.
        output.success(
            "BEA_TOKEN is set in this shell; 'bea cloud logout' leaves it "
            "unchanged and does not revoke it. Unset BEA_TOKEN to stop using it."
        )
        return
    import httpx

    from cli.errors import ConflictError, to_bea_error

    failure: BeaError | None = None
    try:
        response = call(logout.sync_detailed, client=bearer_client(creds.token))
        # A 401 means the server no longer accepts this token: it is already
        # revoked (or expired), which is the outcome logout is after.
        if response.status_code != 401:
            unwrap_or_none(response)
    except httpx.TimeoutException as exc:
        failure = ConflictError(
            f"Removed the local credential, but server revocation timed out ({type(exc).__name__}); "
            "the outcome is unknown. The session may still be valid: revoke it from the dashboard."
        )
    except Exception as exc:
        reason = to_bea_error(exc)
        failure = BeaError(
            f"Removed the local credential, but server revocation failed: {str(reason).rstrip('.')}. "
            "The session may still be valid: revoke it from the dashboard.",
            request_id=reason.request_id,
        )
    # The local credential goes either way: a server that cannot be reached
    # must not leave a token sitting on this disk.
    clear_credentials()
    if failure is not None:
        raise failure
    output.success("Logged out.")


@cloud_app.command("status")
def cloud_status() -> None:
    """Show who is logged in, where the credential came from, and when it expires."""
    ctx = context.current()
    from cli.api.client import bearer_client, call, unwrap_or_none
    from cli.api.rest_client.api.ledger_v_1 import get_user_profile
    from cli.api.rest_client.models import GetUserProfileResponse200Type0
    from cli.auth.credentials import require_credentials
    from cli.errors import error_from_status

    creds = require_credentials()
    response = call(get_user_profile.sync_detailed, client=bearer_client(creds.token))
    user = unwrap_or_none(response, model=GetUserProfileResponse200Type0)
    if user is None and response.status_code != 200:
        # Only a 200 with a null profile means an unrecognized bearer; a 204 or
        # another status the parser skips is not the credential's fault (w5/367).
        from cli.errors import UnreadableSuccess, request_id_from

        raise UnreadableSuccess(
            f"Unexpected server response (HTTP {response.status_code}).",
            status=response.status_code,
            request_id=request_id_from(response.headers),
        )
    if user is None:
        # A revoked or unknown bearer answers this endpoint with an empty
        # profile rather than a 401. Report it exactly the way every other
        # hosted command reports a rejected credential, so a script that
        # branches on the message sees one auth story.
        raise error_from_status(401, f"the server does not recognize this {creds.source} credential")
    # The generated model marks optional fields with `Unset`, which is neither
    # printable nor JSON-serializable; normalize once here.
    username = user.username if isinstance(user.username, str) else None

    if ctx.json_output:
        output.emit(
            {
                "authenticated": True,
                "source": creds.source,
                "expires_at": creds.expire_at,
                "email": user.email,
                "username": username,
                "tier": user.tier,
            },
            target=output.server_target(),
        )
        return

    from cli.utils import single_line

    # Email, username and tier are server text, and the expiry is read from a
    # file: escape them so none can drive the terminal or forge a line.
    typer.echo(f"Source:    {creds.source}")
    typer.echo(f"Expires:   {single_line(creds.expire_at) if creds.expire_at else '(unknown — supplied by BEA_TOKEN)'}")
    typer.echo(f"Email:     {single_line(user.email)}")
    typer.echo(f"Username:  {single_line(username) if username else '(not set)'}")
    typer.echo(f"Tier:      {single_line(user.tier)}")
