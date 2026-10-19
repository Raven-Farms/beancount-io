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
from cli.paths import expand_path
from cli.utils import atomic_write, decode_error_message, regex_reads_otherwise

_NO_COLUMN = "Could not find any valid column in input"
_FORCE = "--force"
# Upstream's default pattern with Beancount's own account grammar: the lexer
# takes any non-ASCII character in a component, upstream's default only ASCII,
# so `Assets:Bank:Épargne` or `Assets:银行` stayed flat in the middle of the
# tree. Written with escapes so the argument itself is plain ASCII.
_LETTERS = r"(?:[A-Za-z0-9-_']|[^\x00-\x7F\s])*"
_COMPONENT = r"(?:[A-Z0-9]|[^\x00-\x7F\s])" + _LETTERS
_ENGLISH_ROOT = r"(?:Assets|Liabilities|Equity|Income|Expenses)"
# Any root the grammar allows, not only the five English names: a ledger with
# `option "name_assets" "Aktiva"` found "no hierarchical column" (w5/414). A
# root needs a component after it, so a capitalized word or a currency is not
# taken for an account. Upstream takes the leftmost column that matches, so a
# narration such as `NYSE:IBM dividend` beside the accounts would win it;
# bea decides the column once per input instead (see `_decide_pattern`).
_ACCOUNT_ANY = rf"(?:{_ENGLISH_ROOT}(?::{_COMPONENT})*|(?:[A-Z]|[^\x00-\x7F\s]){_LETTERS}(?::{_COMPONENT})+)"
# The w5/570 per-position form, kept for input bea cannot pre-scan (a held
# descriptor upstream reads itself): its lookahead rescans to the end of the
# line at every start position, which is quadratic in line length (w5/769).
_ACCOUNT_PATTERN = (
    rf"(?:(?!.*(?<!\S){_ENGLISH_ROOT}:)(?:[A-Z]|[^\x00-\x7F\s]){_LETTERS}(?::{_COMPONENT})+"
    rf"|{_ENGLISH_ROOT}(?::{_COMPONENT})*)"
)
_DEFAULT_DELIMITER = r"[ \t]+"


def _decide_pattern(text: str, delimiter: str | None) -> str:
    """Upstream's pattern with the account column decided once for this input.

    Upstream groups pattern matches by start position and treeifies the
    leftmost valid column, so the narration beside the accounts won it; the
    w5/570 lookahead suppressed the narration only when an English-root
    account followed, and rescanned every line from every position. bea
    runs upstream's own grouping and validity rule here, in linear time,
    then anchors the match to the winning column: an English-root column
    first, else the one with the most components, else the leftmost (w5/769).
    """
    try:
        joined = delimiter if delimiter is not None else _DEFAULT_DELIMITER
        spliced = re.compile(rf"({_ACCOUNT_ANY})(?P<ws>{joined}.|$)")
    except re.error:
        # Upstream splices the same expression and reports it in its own
        # words; bea only stays out of the way.
        return _ACCOUNT_ANY
    beginnings: dict[int, list[re.Match[str]]] = {}
    for line in text.splitlines(keepends=True):
        for match in spliced.finditer(line):
            beginnings.setdefault(match.start(), []).append(match)
    best: tuple[bool, int, int] | None = None
    winner = -1
    for left in sorted(beginnings):
        column = beginnings[left]
        rightmost = max(match.end(1) for match in column)
        following = min(match.end() if match.group("ws") else 10000 for match in column)
        if not rightmost < following:
            continue
        names = [match.group(1) for match in column]
        english = any(re.match(rf"{_ENGLISH_ROOT}:", name) for name in names)
        components = max(name.count(":") + 1 for name in names)
        key = (not english, -components, left)
        if best is None or key < best:
            best, winner = key, left
    if winner <= 0:
        # Leftmost or nothing: upstream agrees without an anchor, and a miss
        # reaches its no-column report.
        return _ACCOUNT_ANY
    return rf"(?<=^.{{{winner}}}){_ACCOUNT_ANY}"


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


def _check_input(name: str | None) -> str | None:
    """Refuse an input path upstream can only fail on, the way `format` does; return a file's text.

    A missing path or a directory exited 1 (`validation`) and an unreadable
    file was not exit 3, each behind upstream's exception class (w5/352).
    A regular file is read here, so its text reaches upstream decoded: a BOM
    split the tree, and Latin-1 failed with a bare `UnicodeDecodeError`
    (w5/723). stdin, a FIFO and a held `/dev/fd/N` read at dispatch.
    """
    if name is None or name == "-" or _held_descriptor(name):
        return None
    path = expand_path(Path(name), "treeify input")
    if not os.path.lexists(path):
        raise UsageError(f"treeify input '{path}' does not exist. Pass a text file, or omit it to read stdin.")
    if path.is_dir():
        raise UsageError(f"treeify input '{path}' is a directory. Pass a text file, or omit it to read stdin.")
    if not path.is_file():
        return None
    if not os.access(path, os.R_OK):
        raise AuthError(f"Cannot read treeify input '{path}': permission denied.")
    return _require_utf8(path.read_bytes(), path)


def _require_utf8(data: bytes, name: object) -> str:
    """The input as text, a BOM skipped, or the shared refusal for bytes that are not UTF-8.

    Upstream decodes strictly since w5/404 and crashed on Latin-1 text with
    a bare `UnicodeDecodeError`, where `format -` names the input and the
    byte (w5/535); it also rendered a BOM file's invisible second root, as
    `format -` never does (w5/723).
    """
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise UsageError(decode_error_message(name, exc, data)) from None


def _read_redirected_input(parsed: argparse.Namespace) -> str | None:
    """Stdin, a FIFO or a held descriptor as text, or None when upstream reads the path itself.

    Upstream reads a named pipe raw, so Latin-1 through `/dev/stdin`,
    `<(…)` or a FIFO failed with a bare `UnicodeDecodeError`; bea reads
    those here instead and passes the text on stdin (w5/723).
    """
    if parsed.input in (None, "-"):
        if sys.stdin is None:
            return None
        return _require_utf8(sys.stdin.buffer.read(), "stdin")
    descriptors = _held_descriptor(parsed.input)
    if descriptors:
        with os.fdopen(os.dup(descriptors[0]), "rb") as stream:
            return _require_utf8(stream.read(), parsed.input)
    path = expand_path(Path(parsed.input), "treeify input")
    if path.is_fifo():
        return _require_utf8(path.read_bytes(), path)
    return None


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
    refuse_misplaced_global("treeify", list(ctx.args), native_options("treeify"), reads="the file", json_output=False)
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
    checked_text: str | None = None
    if parsed is not None and not parsed.help:
        if parsed.input == "-" or parsed.output == "-":
            # Upstream treats '-' as a literal file, unlike bea's stream
            # convention. Translate both sentinels before forwarding or
            # checking aliases; './-' still names a literal file (w5/705).
            if parsed.input == "-":
                parsed.input = None
            if parsed.output == "-":
                parsed.output = None
            forwarded = _without_output(parsed)
        if parsed.filler is not None and not parsed.filler:
            # Upstream pads with `filler * (width // len(filler) + 1)`, so an
            # empty one was a ZeroDivisionError (w5/388).
            raise UsageError("--filler '' is empty; it needs at least one character, such as --filler '.'.")
        _check_regexes(parsed)
        checked_text = _check_input(parsed.input)
    if parsed is not None and parsed.output is not None and not parsed.help:
        # Upstream opens `-o` for writing before it reads the input, so a run
        # that then fails — or reads the same file — has already truncated
        # it. bea keeps the destination itself and writes it only on success.
        destination = expand_path(Path(parsed.output), "--output")
        if destination == Path("-"):
            destination = destination.absolute()  # A literal './-', not the stdout sentinel.
        output.guard_output_destination(
            destination, _ledgers(), refuse_existing_ledger_file=True, force=_FORCE in args[:stop]
        )
        if parsed.input is not None:
            output.refuse_input_alias(destination, expand_path(Path(parsed.input), "treeify input"))
        output.check_output_destination(destination)
        output.require_writable_destination(destination)
        forwarded = _without_output(parsed)
    if parsed is not None and not parsed.help and not parsed.input:
        # Upstream reads stdin when no file is named, a terminal included.
        context.refuse_terminal_stdin(
            "Input is required with --no-input. Name the file to treeify or pipe the text on stdin."
        )
    text = checked_text
    if text is None and parsed is not None and not parsed.help:
        text = _read_redirected_input(parsed)
    if parsed is not None and not (parsed.help or parsed.pattern or parsed.filenames or parsed.loose_accounts):
        # On `parsed` too: dropping the input at dispatch rebuilds the
        # arguments from it, which would otherwise lose this pattern and
        # render non-ASCII components flat (w5/723). The text is in hand by
        # now, so the column is decided from it; the unscannable corner
        # keeps the per-position form (w5/769).
        parsed.pattern = _decide_pattern(text, parsed.delimiter) if text is not None else _ACCOUNT_PATTERN
        forwarded = [f"--pattern={parsed.pattern}", *forwarded]
    if text is None:
        completed = launch.capture_native("treeify", forwarded)
    else:
        if parsed is not None and parsed.input is not None:
            # Upstream reads only the text now; the path stays out so it
            # cannot re-read the raw bytes behind bea's back (w5/723).
            parsed.input = None
            forwarded = _without_output(parsed)
        completed = launch.capture_native("treeify", forwarded, input_text=text)
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
        output.utf8_stdout()
        output.replay(completed.stdout, sys.stdout)
    output.replay(completed.stderr, sys.stderr)


def _ledgers() -> list[Path]:
    """The ledger under read, when there is one — treeify runs happily without."""
    try:
        return [context.current().entry_file()]
    except UsageError:
        return []
