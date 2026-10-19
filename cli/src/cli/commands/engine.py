"""`bea engine` — manage the isolated Beancount engine and optional features.

The base engine (Beancount + Beanquery + helper) provisions on first use.
Optional Beangulp and Beanprice stay out of that base profile and out of the
frontend: enable them explicitly with `bea engine enable`.
"""

from __future__ import annotations

from typing import Annotated

import typer

from cli import context, output
from cli.engine import launch, paths, provision

engine_app = typer.Typer(
    name="engine",
    help="Manage the Beancount engine and its optional features.",
    no_args_is_help=True,
)

_TIER_LABELS = {
    "override": f"{paths.PYTHON_ENV} override",
    "managed": "managed engine",
    "checkout": "checkout",
    "first-use": "not provisioned; provisions on first use",
}


@engine_app.command("status")
def engine_status() -> None:
    """Show which engine serves local commands.

    Reports whether the engine is provisioned and which optional features are enabled.
    """
    output.utf8_stdout()
    source = launch.resolve_engine()
    status = {
        **provision.feature_status(),
        "serving": {"tier": source.tier, "location": str(source.location)},
    }
    # Present is not usable: package directories whose contents were damaged
    # still read as provisioned while every command failed to import (w5/320),
    # and an override that cannot run the engine read as serving while every
    # local command sent the user back here (w5/481).
    probed = source.tier in ("managed", "override") and source.python is not None
    failure = launch.engine_load_failure(source.python) if probed and source.python else None
    reason = f"it cannot load the engine ({failure})" if failure is not None else None
    if failure is None and source.tier == "override" and source.python is not None:
        # Native tools are run from beside the override, so loading the engine
        # is not enough: `check` and `example` failed where status said usable (w5/647).
        missing = launch.missing_native_tools(source.python)
        if missing:
            failure = reason = f"no {', '.join(missing)} beside {source.python} ({paths.bin_dir_for(source.python)})"
    if probed:
        status["usable"] = failure is None
    if failure is not None:
        status["damaged" if source.tier == "managed" else "unusable"] = failure
    damaged = failure if source.tier == "managed" else None
    if context.current().json_output:
        output.emit(status)
        return

    override = status.get("python_override")
    if override:
        typer.echo(f"Engine interpreter override: {override}")
        if reason is not None:
            typer.echo(f"Usable: no — {reason}. Correct or unset {paths.PYTHON_ENV}; local commands fail until then.")
    else:
        typer.echo(f"Engine {status['engine_version']} at {status['engine_root']}")
        if damaged is not None:
            typer.echo(
                f"Provisioned: damaged — the engine cannot load ({damaged}). "
                f"Remove {paths.engine_root()} and rerun; bea provisions a fresh engine."
            )
        elif status["provisioned"]:
            typer.echo("Provisioned: yes")
        elif paths.engine_root().exists():
            typer.echo("Provisioned: no (the engine there is incomplete; the next local command rebuilds it)")
        else:
            typer.echo("Provisioned: no")
    typer.echo(f"Serving from: {_TIER_LABELS[source.tier]} ({source.location})")

    features = status.get("features") or {}
    if not features:
        typer.echo("Optional features: (none defined)")
        return
    typer.echo("Optional features:")
    for name, info in features.items():
        state = "enabled" if info.get("enabled") else "disabled"
        present = "present" if info.get("present") else "absent"
        typer.echo(f"  {name}: {state}, {present} ({info.get('license')})")
        notes = info.get("notes")
        if notes:
            typer.echo(f"    {notes}")


def _complete_feature(incomplete: str) -> list[str]:
    """The optional features the shipped manifest defines (w5/421)."""
    return [name for name in sorted(provision.optional_features()) if name.startswith(incomplete)]


@engine_app.command("enable")
def engine_enable(
    feature: Annotated[
        str,
        typer.Argument(
            help="Optional engine feature to provision: beangulp or beanprice", autocompletion=_complete_feature
        ),
    ],
) -> None:
    """Install a reviewed optional package.

    The package goes into the managed engine, never into the bea frontend.
    """
    name = feature.strip().lower()
    changed, enabled = provision.enable_feature(name)
    payload = {
        "feature": name,
        "changed": changed,
        "already_enabled": not changed,
        "enabled": sorted(enabled),
        "engine_root": str(paths.engine_root()),
        "engine_version": paths.engine_version(),
    }
    if context.current().json_output:
        output.emit(payload)
        return
    if changed:
        output.success(f"Enabled '{name}' in the managed engine. It is not installed into the bea frontend.")
