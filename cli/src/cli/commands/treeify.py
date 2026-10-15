"""`bea treeify` — delegate to upstream `treeify`."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import NoReturn

import typer

from cli import context, output
from cli.engine import launch
from cli.errors import AuthError, UsageError, refuse_json, refuse_misplaced_global
from cli.native_help import native_options
from cli.utils import atomic_write, regex_reads_otherwise

_NO_COLUMN = "Could not find any valid column in input"
_FORCE = "--force"
# Upstream's default pattern with Beancount's own account grammar: the lexer
# takes any non-ASCII character in a component, upstream's default only ASCII,
# so `Assets:Bank:Épargne` or `Assets:银行` stayed flat in the middle of the
# tree. Written with escapes so the argument itself is plain ASCII.
_LETTERS = r"(?:[A-Za-z0-9-_']|[^\x00-\x7F\s])*"
_COMPONENT = r"(?:[A-Z0-9]|[^\x00-\x7F\s])" + _LETTERS
# Any root the grammar allows, not only the five English names: a ledger with
# `option "name_assets" "Aktiva"` found "no hierarchical column" (w5/414). A
# root needs a component after it, so a capitalized word or a currency is not
# taken for an account; the English roots still match on their own.
_ACCOUNT_PATTERN = (
    rf"(?:(?:[A-Z]|[^\x00-\x7F\s]){_LETTERS}(?::{_COMPONENT})+"
    r"|Assets|Liabilities|Equity|Income|Expenses)"
)


class _Unparsed(Exception):
    """The arguments are not ones upstream accepts; it reports that itself."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise _Unparsed(message)


def _upstream_parser() -> _Parser:
    """Upstream treeify's argument grammar, so `bea` reads argv as it will.

    Mirrors `beancount/tools/treeify.py`: the same options, argparse's default
    abbreviation of long options and clustering of short flags. Reading the
    destination any other way is how `--outp X` or `-Ao X` slipped past the
    guard and overwrote a ledger.
    """
    parser = _Parser(add_help=False)
    parser.add_argument("input", nargs="?")
    parser.add_argument("-h", "--help", action="store_true")
    parser.add_argument("-o", "--output")
    parser.add_argument("-r", "--pattern")
    parser.add_argument("-d", "--delimiter")
    parser.add_argument("-s", "--split")
    parser.add_argument("-F", "--filenames", action="store_true")
    parser.add_argument("-A", "--loose-accounts", action="store_true")
    parser.add_argument("--filler")
    return parser


def _without_output(parsed: argparse.Namespace) -> list[str]:
    """The same invocation with stdout as the destination."""
    argv: list[str] = []
    for flag, value in (
        ("--pattern", parsed.pattern),
        ("--delimiter", parsed.delimiter),
        ("--split", parsed.split),
        ("--filler", parsed.filler),
    ):
        if value is not None:
            argv.append(f"{flag}={value}")
    if parsed.filenames:
        argv.append("--filenames")
    if parsed.loose_accounts:
        argv.append("--loose-accounts")
    if parsed.input is not None:
        argv += ["--", parsed.input]
    return argv


def _check_regexes(parsed: argparse.Namespace) -> None:
    """Refuse a malformed regex option by name, before upstream trips over it.

    Upstream splices `--pattern` and `--delimiter` into one larger expression,
    so a typo surfaces as `IndexError: no such group` or as a position inside
    text the user never typed. Only the values upstream will use are checked:
    `--filenames` and `--loose-accounts` replace the split, and conflict with
    a pattern in upstream's own words.
    """
    preset = parsed.filenames or parsed.loose_accounts
    for flag, value, used in (
        ("--pattern", parsed.pattern, not preset),
        ("--delimiter", parsed.delimiter, True),
        ("--split", parsed.split, not preset),
    ):
        if value is None or not used:
            continue
        # First, so the compile below never warns: upstream would only warn,
        # then split on something else (w5/429).
        otherwise = regex_reads_otherwise(value)
        if otherwise is not None:
            raise UsageError(f"Invalid regular expression for {flag} {value!r}: {otherwise}.")
        try:
            re.compile(value)
        except re.error as exc:
            raise UsageError(
                f"Invalid regular expression for {flag} {value!r}: {exc}. "
                "Fix the expression; see 'bea treeify --help' for the defaults."
            ) from None


def _check_input(name: str | None) -> None:
    """Refuse an input path upstream can only fail on, the way `format` does.

    A missing path or a directory exited 1 (`validation`) and an unreadable
    file was not exit 3, each behind upstream's exception class (w5/352).
    stdin and a held `/dev/fd/N` pass through untouched.
    """
    if name is None or name == "-" or _held_descriptor(name):
        return
    path = Path(name).expanduser()
    if not os.path.lexists(path):
        raise UsageError(f"treeify input '{path}' does not exist. Pass a text file, or omit it to read stdin.")
    if path.is_dir():
        raise UsageError(f"treeify input '{path}' is a directory. Pass a text file, or omit it to read stdin.")
    if path.is_file() and not os.access(path, os.R_OK):
        raise AuthError(f"Cannot read treeify input '{path}': permission denied.")


def _held_descriptor(name: str | None) -> tuple[int, ...]:
    """The descriptor a `/dev/fd/N` input names, when this process holds it open.

    Process substitution (`<(…)`) names its pipe that way, and the child,
    started with its standard streams alone, could not open it: `OSError: Bad
    file descriptor` (w5/436). Passed on, the child reads it as a file.
    """
    match = re.fullmatch(r"/dev/fd/(\d+)", name or "")
    if match is None:
        return ()
    try:
        os.fstat(int(match.group(1)))
    except OSError:
        return ()
    return (int(match.group(1)),)


def treeify(ctx: typer.Context) -> None:
    """Render a column as an ASCII tree (delegates to treeify)."""
    refuse_json("treeify", hint="Run without --json to print the ASCII tree.")
    refuse_misplaced_global("treeify", list(ctx.args), native_options("treeify"))
    # Upstream treeify knows no `--force`, so bea's own opt-in is stripped
    # before forwarding; without it an existing ledger file is never replaced.
    args = list(ctx.args)
    stop = args.index("--") if "--" in args else len(args)
    forwarded = [arg for index, arg in enumerate(args) if arg != _FORCE or index > stop]
    destination: Path | None = None
    try:
        parsed = _upstream_parser().parse_args(forwarded)
    except _Unparsed:
        # Upstream rejects these before it opens anything; the plain-spelling
        # guard still runs in case its grammar ever drifts from the mirror.
        parsed = None
        output.guard_forwarded_output(
            forwarded, _ledgers(), refuse_existing_ledger_file=True, force=_FORCE in args[:stop], flags="FA"
        )
    if parsed is not None and not parsed.help:
        _check_regexes(parsed)
        _check_input(parsed.input)
    if parsed is not None and parsed.output is not None and not parsed.help:
        # Upstream opens `-o` for writing before it reads the input, so a run
        # that then fails — or reads the same file — has already truncated
        # it. bea keeps the destination itself and writes it only on success.
        destination = Path(parsed.output).expanduser()
        output.guard_output_destination(
            destination, _ledgers(), refuse_existing_ledger_file=True, force=_FORCE in args[:stop]
        )
        if parsed.input is not None:
            output.refuse_input_alias(destination, Path(parsed.input).expanduser())
        output.check_output_destination(destination)
        output.require_writable_destination(destination)
        forwarded = _without_output(parsed)
    if parsed is not None and not (parsed.help or parsed.pattern or parsed.filenames or parsed.loose_accounts):
        forwarded = [f"--pattern={_ACCOUNT_PATTERN}", *forwarded]
    if parsed is not None and not parsed.help and not parsed.input:
        # Upstream reads stdin when no file is named, a terminal included.
        context.refuse_terminal_stdin(
            "Input is required with --no-input. Name the file to treeify or pipe the text on stdin."
        )
    descriptors = _held_descriptor(parsed.input if parsed is not None else None)
    if descriptors:
        completed = launch.capture_native("treeify", forwarded, pass_fds=descriptors)
    else:
        completed = launch.capture_native("treeify", forwarded)
    if completed.returncode == 0 and _NO_COLUMN in (completed.stderr or ""):
        # Upstream echoes the input unchanged and calls that success; the
        # echo is not a tree, so it is not printed.
        output.replay(completed.stderr, sys.stderr)
        raise UsageError(
            "treeify found no hierarchical column to render (colon-separated names like Assets:Cash). "
            "Pipe balances or an account listing, not plain text; for names outside Beancount's account "
            "grammar, pass -A (loose accounts) or your own -r pattern."
        )
    launch.check_native(completed, "treeify")
    if destination is not None:
        atomic_write(destination, completed.stdout or "", export=True)
    else:
        output.replay(completed.stdout, sys.stdout)
    output.replay(completed.stderr, sys.stderr)


def _ledgers() -> list[Path]:
    """The ledger under read, when there is one — treeify runs happily without."""
    try:
        return [context.current().entry_file()]
    except UsageError:
        return []
