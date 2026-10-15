"""`bea price` — managed price status and refresh, or upstream `bean-price`.

`status` and `refresh` report the ledger's managed price includes; anything
else forwards to bean-price exactly as before (requires `bea engine enable
beanprice`). Recording a supplied quote remains `bea add price` and does not
need Beanprice.
"""

from __future__ import annotations

import os
from typing import Any

import typer

from cli import context, output
from cli.engine import launch
from cli.errors import LedgerError, UsageError, refuse_json, refuse_misplaced_global
from cli.native_command import ForwardingCommand
from cli.native_help import native_options

#: `price`'s own verbs; anything else is forwarded to bean-price.
_VERBS = {
    "status": "List managed price sources with their freshness",
    "refresh": "Re-resolve managed price sources now",
    "export": "Snapshot a portable copy with local price files",
}


class PriceCommand(ForwardingCommand):
    """The `price` command, whose own verbs complete in place of file names (w5/421)."""

    def shell_complete(self, ctx: Any, incomplete: str) -> list[Any]:
        from typer._click.shell_completion import CompletionItem

        items: list[Any] = super().shell_complete(ctx, incomplete)
        if ctx.args or incomplete.startswith("-"):
            return items
        return [CompletionItem(verb, help=text) for verb, text in _VERBS.items() if verb.startswith(incomplete)] + items


def price(ctx: typer.Context) -> None:
    """Inspect managed price includes, or fetch bean-price quotes.

    `status` lists every managed source with its freshness, revision, and
    errors; `refresh` re-resolves now and reports what changed; `export`
    snapshots a portable copy with local price files. Anything else forwards
    to bean-price (requires `bea engine enable beanprice`), so a quotes job
    file named `status` must be passed by path.
    """
    args = list(ctx.args)
    refuse_misplaced_global("price", args, native_options("price"))
    if args[:1] == ["status"]:
        _status(args[1:])
        return
    if args[:1] == ["refresh"]:
        _refresh(args[1:])
        return
    if args[:1] == ["export"]:
        _export(args[1:])
        return
    refuse_json(
        "price",
        when="when it forwards to bean-price",
        hint="Run without --json to print price directives; bea price status, refresh and export answer in JSON.",
    )
    # bean-price loads a ledger named as a source file; its load cache goes
    # where every other load's does, not beside the ledger (w5/456).
    ledger = next((arg for arg in args if not arg.startswith("-") and os.path.isfile(arg)), None)
    if ledger:
        code = launch.run_optional_native("beanprice", "bean-price", args, ledger=os.path.abspath(ledger))
    else:
        code = launch.run_optional_native("beanprice", "bean-price", args)
    raise typer.Exit(code)


def _answer(argv: list[str], *, table_covers_sources: bool = False) -> dict[str, Any]:
    """The helper answer, with the load's own errors bannered, never raised.

    `price status` and `price refresh` show each managed source's state in
    their own table, so the load's "source unavailable … Run bea price status
    to inspect the source." told the user to run the command they had just
    run, and repeated the row below it (w5/354). There it is left out.
    """
    data = launch.helper_json(argv)
    errors = data.get("errors") or []
    if table_covers_sources:
        errors = [error for error in errors if "managed price source unavailable" not in str(error)]
    output.render_ledger_errors(errors, allow=True)
    return data


def _status(extra: list[str]) -> None:
    if extra:
        raise UsageError(f"bea price status takes no arguments; got: {' '.join(extra)}.")
    current = context.current()
    file = current.entry_file()
    sources: list[dict[str, Any]] = _answer(["price-status", "--file", str(file)], table_covers_sources=True)["sources"]
    if current.json_output:
        output.emit({"sources": sources}, target=output.file_target(file))
        return
    if not sources:
        typer.echo("No managed price includes in this ledger.")
        return
    output.table(
        ["ALIAS", "FRESHNESS", "REVISION", "OBSERVED AT", "NEXT REFRESH", "SHADOWED", "ERROR"],
        [
            [
                str(source["alias"]),
                str(source["freshness"]),
                str(source["revision"] or "-"),
                str(source["observed_at"] or "-"),
                str(source["next_refresh_at"] or "-"),
                str(source["shadowed_count"]),
                str(source["error"] or ""),
            ]
            for source in sources
        ],
    )


def _refresh(extra: list[str]) -> None:
    if extra:
        raise UsageError(f"bea price refresh takes no arguments; got: {' '.join(extra)}.")
    current = context.current()
    file = current.entry_file()
    data = _answer(["price-refresh", "--file", str(file)], table_covers_sources=True)
    sources: list[dict[str, Any]] = data["sources"]
    failed = [
        source
        for source in sources
        if source["error"]
        or source["freshness"] == "unavailable"
        or (data.get("strict_prices") and source["freshness"] == "stale")
    ]
    if failed:
        raise LedgerError(
            "Price refresh failed for " + ", ".join(source["alias"] for source in failed) + ".",
            details=[
                f"{source['alias']}: {source['error'] or source['freshness']}; "
                f"serving revision {source['revision'] or 'none'}"
                for source in sources
            ],
            result={"sources": sources, "changed": data["changed"]},
        )
    if current.json_output:
        output.emit({"sources": sources, "changed": data["changed"]}, target=output.file_target(file))
        return
    if not sources:
        typer.echo("No managed price includes in this ledger.")
        return
    changed = {item["url"]: item for item in data["changed"]}
    for source in sources:
        if source["freshness"] == "unavailable":
            typer.echo(f"{source['alias']}: still unavailable ({source['error'] or 'no cached revision'})")
        elif source["url"] in changed:
            item = changed[source["url"]]
            before = item["previous_revision"] or "none"
            typer.echo(f"{source['alias']}: {before} → {item['revision']}")
        else:
            typer.echo(f"{source['alias']}: unchanged at {source['revision']}")


def _export(args: list[str]) -> None:
    output_dir: str | None = None
    allow_errors = False
    force = False
    pending = list(args)
    while pending:
        arg = pending.pop(0)
        if arg in ("--output", "-o"):
            if not pending:
                raise UsageError("bea price export --output needs a directory.")
            output_dir = pending.pop(0)
        elif arg.startswith("--output="):
            output_dir = arg.split("=", 1)[1]
            if not output_dir:
                raise UsageError("bea price export --output needs a directory.")
        elif arg == "--allow-errors":
            allow_errors = True
        elif arg == "--force":
            force = True
        else:
            raise UsageError(f"bea price export takes only --output, --allow-errors and --force; got: {arg}.")
    current = context.current()
    file = current.entry_file()
    argv = ["price-export", "--file", str(file)]
    if output_dir is not None:
        argv += ["--output", output_dir]
    if allow_errors:
        argv.append("--allow-errors")
    if force:
        argv.append("--force")
    data = _answer(argv)
    if current.json_output:
        output.emit(
            {
                "output": data["output"],
                "files": data["files"],
                "overwritten": data.get("overwritten") or [],
                "sources": data["sources"],
            },
            # Absolute, as every target path is: `-o exp` came back as `exp` (w5/324).
            target={**output.file_target(file), "into": os.path.abspath(data["output"])},
        )
        return
    files: list[str] = data["files"]
    output.success(f"Exported {len(files)} file{'s' if len(files) != 1 else ''} to {data['output']}.")
    overwritten: list[str] = data.get("overwritten") or []
    if overwritten:
        output.note(f"Overwrote {len(overwritten)} existing file(s) (--force): " + ", ".join(overwritten))
