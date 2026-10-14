"""`bea example` — delegate to upstream `bean-example`."""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

import typer

from cli import context
from cli.engine import launch
from cli.errors import BeaError, ConflictError, UsageError, refuse_json
from cli.output import (
    check_output_destination,
    forwarded_option,
    refuse_include_claim,
    replay,
    require_writable_destination,
)
from cli.utils import atomic_write

_FORCE = "--force"

#: How upstream reports an error in the history it just generated: it loads the
#: text from a string, so every diagnostic starts `<string>:LINE:`.
_VALIDATION_ERROR = re.compile(r"^<string>:\d+:\s*(\S.*)$", re.MULTILINE)


def _split_output(args: list[str]) -> tuple[list[str], Path | None, bool]:
    """Pull bea's own `--force` and upstream's `-o` out of the passthrough args.

    `bean-example` knows no `--force`, so it is stripped before forwarding;
    `-o`/`--output` stays, since upstream is what writes it. Only an existing
    destination needs refusing — a fresh path is upstream's normal case.
    """
    stop = args.index("--") if "--" in args else len(args)
    force = _FORCE in args[:stop]
    forwarded = [arg for index, arg in enumerate(args) if arg != _FORCE or index > stop]
    value = forwarded_option(forwarded, "-o", "--output")
    return forwarded, None if value is None else Path(value), force


def _without_output(args: list[str]) -> list[str]:
    """The same invocation with stdout as the destination.

    Drops the spellings `forwarded_option` reads — `-o X`, `-oX`, `--output X`,
    `--output=X` — and leaves a value-less `-o` for upstream to reject.
    """
    kept: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--":
            kept += args[index:]
            break
        if arg in ("-o", "--output") and index + 1 < len(args):
            index += 2
            continue
        if not (arg.startswith("--output=") or (arg.startswith("-o") and len(arg) > 2)):
            kept.append(arg)
        index += 1
    return kept


def _refuse_invalid(diagnostic: str, destination: Path | None) -> None:
    """Fail a run whose generated history upstream's own validation rejected.

    `bean-example` validates what it generated, logs the loader's errors and
    still exits 0 — after writing the file. Its rules assume whole calendar
    years: a range starting mid-year leaves a `balance ... 0 IRAUSD` assertion
    that fails, so the "example" does not pass `bea check` (w5/136).
    """
    errors = _VALIDATION_ERROR.findall(diagnostic)
    if not errors:
        return
    kept = "nothing was printed" if destination is None else f"{destination} was not written"
    raise BeaError(
        f"bean-example generated a ledger that fails validation ({len(errors)} "
        f"error{'' if len(errors) == 1 else 's'}), so {kept}. "
        "Its rules assume whole calendar years: start --date-begin on January 1, with --date-birth before it.",
        details=errors[:5],
    )


def example(ctx: typer.Context) -> None:
    """Generate an example ledger (delegates to bean-example)."""
    refuse_json("example", hint="Run without --json to print the sample ledger.")
    forwarded, output, force = _split_output(list(ctx.args))
    if output is not None and not force and (output.exists() or output.is_symlink()):
        raise ConflictError(
            f"Already exists: {output}. Pass --force to overwrite it with a generated example; "
            "without it, example never overwrites."
        )
    if output is not None:
        # No ledger is read here, so `--force` may replace any file — but a
        # path the working ledger's includes would claim merges a generated
        # history into the books, forced or not.
        try:
            ledger = context.current().entry_file()
        except UsageError:
            ledger = None
        if ledger is not None:
            refuse_include_claim(output.expanduser(), ledger)
    _check_date_order(forwarded)
    destination: Path | None = None
    if output is not None and str(output) != "-":
        # Upstream writes `-o` first and validates afterwards, so a history it
        # rejects is already on disk. bea keeps the destination itself and
        # writes it only once the run and its validation have succeeded.
        destination = output
        check_output_destination(destination)
        require_writable_destination(destination)
        forwarded = _without_output(forwarded)
    completed = launch.capture_native("bean-example", forwarded)
    launch.check_native(completed, "bean-example")
    _refuse_invalid(completed.stderr or "", destination)
    if destination is not None:
        atomic_write(destination, completed.stdout or "", export=True)
    else:
        replay(completed.stdout, sys.stdout)
    replay(completed.stderr, sys.stderr)


#: The shortest range bean-example reliably generates. Its rules schedule
#: monthly entries, and a shorter range crashes it with IndexError or
#: StopIteration (30 days still fails for some seeds; 31 never did).
_MIN_SPAN_DAYS = 31


def _check_date_order(args: list[str], today: date | None = None) -> None:
    """Refuse a date range bean-example cannot generate before upstream dies on it.

    A missing side takes upstream's default (January 1 two years back, and
    today), so a lone `--date-end` in the past or `--date-begin` in the
    future is caught as inverted too. Only ISO dates are compared; anything
    else passes through to upstream's own parsing.
    """
    values: dict[str, str] = {}
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--":
            break
        if arg in ("--date-begin", "--date-end") and index + 1 < len(args):
            values[arg] = args[index + 1]
            index += 2
            continue
        if arg.startswith("--date-begin="):
            values["--date-begin"] = arg.split("=", 1)[1]
        elif arg.startswith("--date-end="):
            values["--date-end"] = arg.split("=", 1)[1]
        index += 1
    if not values:
        return
    today = today or date.today()
    try:
        begin = date.fromisoformat(values["--date-begin"]) if "--date-begin" in values else date(today.year - 2, 1, 1)
        end = date.fromisoformat(values["--date-end"]) if "--date-end" in values else today
    except ValueError:
        return
    shown_begin = f"--date-begin {begin.isoformat()}" + ("" if "--date-begin" in values else " (default)")
    shown_end = f"--date-end {end.isoformat()}" + ("" if "--date-end" in values else " (default: today)")
    if begin > end:
        raise UsageError(f"{shown_begin} is after {shown_end}; begin must be on or before end.")
    if (end - begin).days < _MIN_SPAN_DAYS:
        raise UsageError(
            f"{shown_begin} to {shown_end} spans {(end - begin).days} days; "
            f"bean-example needs at least {_MIN_SPAN_DAYS}."
        )
