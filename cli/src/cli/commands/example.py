"""`bea example` — delegate to upstream `bean-example`."""

from __future__ import annotations

import re
import stat
import sys
from datetime import date
from pathlib import Path

import typer

from cli import context
from cli.engine import launch
from cli.errors import BeaError, ConflictError, UsageError, refuse_json, refuse_misplaced_global
from cli.native_help import native_options
from cli.output import (
    check_output_destination,
    forwarded_option,
    note,
    refuse_include_claim,
    replay,
    require_writable_destination,
    utf8_stdout,
)
from cli.paths import expand_path
from cli.utils import atomic_write

_FORCE = "--force"

#: How upstream reports an error in the history it just generated: it loads the
#: text from a string, so every diagnostic starts `<string>:LINE:`.
_VALIDATION_ERROR = re.compile(r"^<string>:\d+:\s*(\S.*)$", re.MULTILINE)

#: The errors a range starting mid-year produces: a yearly assertion that
#: fails, or a posting before an account's first open (w5/136).
_CALENDAR_ERROR = re.compile(r"Balance failed|inactive account")

#: A line only a ledger holds: a dated directive or an option.
_DIRECTIVE = re.compile(r"^(?:\d{4}-\d{2}-\d{2}\s|option\s)", re.MULTILINE)


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
    return forwarded, None if value is None else expand_path(Path(value), "--output"), force


def _is_written_through(output: Path) -> bool:
    """Whether `-o` names a device or FIFO, which is written through, not replaced.

    `-o /dev/null` exists, but there is no file to overwrite and so nothing for
    `--force` to consent to (w5/277). A directory stays a conflict.
    """
    try:
        mode = output.stat().st_mode
    except OSError:
        return False
    return not stat.S_ISREG(mode) and not stat.S_ISDIR(mode)


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
    # The calendar advice fits only the errors a mid-year start makes; a long
    # span that starts on January 1 fails otherwise (`Amount is zero`), and was
    # told to do what it had already done (w5/573).
    if any(_CALENDAR_ERROR.search(error) for error in errors):
        advice = "Its rules assume whole calendar years: start --date-begin on January 1, with --date-birth before it."
    else:
        advice = "A span this long is more than it generates cleanly; try a shorter one with an earlier --date-end."
    raise BeaError(
        f"bean-example generated a ledger that fails validation ({len(errors)} "
        f"error{'' if len(errors) == 1 else 's'}), so {kept}. {advice}",
        details=errors[:5],
    )


def example(ctx: typer.Context) -> None:
    """Generate an example ledger (delegates to bean-example)."""
    refuse_json("example", hint="Run without --json to print the sample ledger.")
    refuse_misplaced_global("example", list(ctx.args), native_options("example"), reads="", json_output=False)
    forwarded, output, force = _split_output(list(ctx.args))
    if "--version" in forwarded[: forwarded.index("--") if "--" in forwarded else None]:
        # Informational: bean-example prints its version and exits 0, which
        # with -o wrote "Beancount 3.2.3" as the generated ledger, and with
        # --force replaced one (w5/415).
        if output is not None:
            note(f"--version prints bean-example's version; {output} was not written.")
        version = launch.capture_native("bean-example", ["--version"])
        launch.check_native(version, "bean-example")
        replay(version.stdout, sys.stdout)
        return
    # A directory is never a file to overwrite: the conflict and its
    # `--force` advice led to a directory refusal that --force cannot pass;
    # it now gets that refusal straight away (w5/353).
    if (
        output is not None
        and not force
        and (output.exists() or output.is_symlink())
        and not output.is_dir()
        and not _is_written_through(output)
    ):
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
            refuse_include_claim(expand_path(output, "--output"), ledger)
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
        if not _DIRECTIVE.search(completed.stdout or ""):
            # Whatever else upstream printed and called success, it is not a
            # ledger to write over the destination (w5/415).
            raise BeaError(f"bean-example printed no ledger, so {destination} was not written.")
        atomic_write(destination, completed.stdout or "", export=True)
    else:
        utf8_stdout()
        replay(completed.stdout, sys.stdout)
    replay(completed.stderr, sys.stderr)


#: The shortest range bean-example reliably generates. Its rules schedule
#: monthly entries, and a shorter range crashes it with IndexError or
#: StopIteration (30 days still fails for some seeds; 31 never did).
_MIN_SPAN_DAYS = 31

#: The earliest history bean-example generates: it validates nothing dated
#: before the Unix epoch, and `0001-01-01` ran a minute, then failed with
#: `decimal.InvalidOperation` (w5/390).
_EARLIEST_BEGIN = date(1970, 1, 1)

#: The longest span bea asks for. 26 years generate in seconds; `--date-end
#: 9999-12-31` ran about three minutes, then failed with `OverflowError`.
_MAX_SPAN_YEARS = 100

#: `date.fromisoformat` also reads `20260301` and week dates; the range check
#: takes the one spelling bea and upstream are certain to read alike.
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _check_date_order(args: list[str], today: date | None = None) -> None:
    """Refuse a date range bean-example cannot generate before upstream dies on it.

    A missing side takes upstream's default (January 1 two years back, and
    today), so a lone `--date-end` in the past or `--date-begin` in the
    future is caught as inverted too. Only `YYYY-MM-DD` is accepted: upstream
    reads looser spellings (`2026/03/01`, `March 1 2026`) with a parser the
    frontend does not carry, so those would reach it unchecked (w5/275).
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
    begin = _iso_date("--date-begin", values) or date(today.year - 2, 1, 1)
    end = _iso_date("--date-end", values) or today
    shown_begin = f"--date-begin {begin.isoformat()}" + ("" if "--date-begin" in values else " (default)")
    shown_end = f"--date-end {end.isoformat()}" + ("" if "--date-end" in values else " (default: today)")
    if begin > end:
        raise UsageError(f"{shown_begin} is after {shown_end}; begin must be on or before end.")
    if (end - begin).days < _MIN_SPAN_DAYS:
        raise UsageError(
            f"{shown_begin} to {shown_end} spans {(end - begin).days} days; "
            f"bean-example needs at least {_MIN_SPAN_DAYS}."
        )
    if begin < _EARLIEST_BEGIN:
        raise UsageError(
            f"{shown_begin} is before {_EARLIEST_BEGIN.isoformat()}; bean-example cannot generate a history "
            "that early. Choose a later --date-begin."
        )
    if end.year - begin.year > _MAX_SPAN_YEARS or (
        end.year - begin.year == _MAX_SPAN_YEARS and (end.month, end.day) > (begin.month, begin.day)
    ):
        raise UsageError(
            f"{shown_begin} to {shown_end} spans more than {_MAX_SPAN_YEARS} years; bea example generates at most "
            f"{_MAX_SPAN_YEARS} (a longer span runs for minutes, then fails upstream). Narrow the range."
        )


def _iso_date(option: str, values: dict[str, str]) -> date | None:
    """The option's value as a date, or None when the option was not given."""
    if option not in values:
        return None
    value = values[option]
    try:
        if not _ISO_DATE.fullmatch(value):
            raise ValueError(value)
        return date.fromisoformat(value)
    except ValueError:
        raise UsageError(f"{option} {value!r} is not a calendar date in ISO form; write it as YYYY-MM-DD.") from None
