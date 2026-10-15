"""`bea check` — native bean-check, with bea's JSON envelope via the helper."""

from __future__ import annotations

import re
import shlex
import unicodedata
from pathlib import Path

import typer

from cli import context, output
from cli.engine import launch
from cli.errors import BeaError, LedgerError, UsageError

_URL_INCLUDE_RE = re.compile(r'^\s*include\s*"(?i:https?)://', re.MULTILINE)
"""An include line native bean-check cannot resolve (w1/m29).

A posting line can never match: account names cannot start with the lowercase
`include` keyword, and a `;` comment never has the keyword first. Close
enough to exact for routing the closure to the helper check. The scheme is
matched in any case and the keyword may touch its string, the way the loader
and the include scanner read it (w5/192).
"""

_PROSE_RE = re.compile(r'"(?:[^"\\]|\\.)*"|;[^\n]*|^\*[^\n]*', re.MULTILINE)
"""String literals, `;` comments, and org-mode `*` heading lines.

Their text never names an account, so bean-check reads it byte for byte
whatever its Unicode normalization; only the remaining tokens decide whether
NFC and NFD spellings could split one account in two (w1/054).
"""


def check(ctx: typer.Context) -> None:
    """Parse, check and realize a beancount ledger."""
    current = context.current()
    file = current.entry_file()
    compat = _closure_needs_compat(file)
    if compat is not None and not current.json_output:
        # Native bean-check cannot parse a BOM-marked file at all, reads
        # NFC and NFD spellings of one account as two accounts, and cannot
        # fetch URL includes, so these closures run the helper check in both
        # modes; bean-check-only flags cannot be forwarded to a run that
        # never starts upstream.
        if ctx.args:
            tokens = " ".join(ctx.args)
            reason, advice = compat
            raise UsageError(f"bea check cannot pass bean-check options ({tokens}) for this ledger: {reason}. {advice}")
        launch.helper_json(["check", "--file", str(file)])
        raise typer.Exit(0)
    if current.json_output:
        # Keep bea's documented JSON envelope; native --json is a different shape.
        # bean-check-only flags (-v, --auto, …) are not implemented on bea-engine
        # check — refuse them up front as usage, not as a false "engine did not answer".
        if ctx.args:
            tokens = " ".join(ctx.args)
            raise UsageError(
                f"bea --json check does not accept bean-check options ({tokens}). "
                "Drop --json to use native bean-check flags such as -v / --auto."
            )
        data = launch.helper_json(["check", "--file", str(file)])
        output.emit(data, target=output.file_target(file))
        return
    # Judged as given, with or without --no-cache, as USAGE promises.
    _refuse_cache_over_ledger(file, ctx.args)
    args = list(ctx.args)
    if _disables_cache(args) and _names_cache_file(args):
        # bean-check ignores the path under --no-cache and says so through
        # Python's root logger, a raw `WARNING:root:` line (w5/417).
        output.note("--no-cache turns the load cache off, so --cache-filename is ignored.")
        args = _without_cache_file(args)
    if output.has_unreadable_include(file) or output.has_duplicate_member(file):
        # bean-check answers an include it cannot open with a traceback, and
        # loads a file reached under two names twice without a word; the
        # helper names the include and the file that includes it (w5/120),
        # or both names of the one file (w5/433).
        launch.helper_json(["check", "--file", str(file)])
    # bean-check keys its load cache on the files read, not on the plugin set,
    # and every later read trusts that cache. A load made with the auto plugins
    # must neither be stored there nor answered from a default load's entry (w5/111).
    isolate = ["--no-cache"] if _enables_auto(args) else []
    # bean-check does not cover document paths that resolve outside the ledger tree;
    # the helper check does, so copies that still resolve against another tree fail.
    # Only that rule: this second load knows none of bean-check's options, so
    # re-judging validity failed a ledger `--auto` had just accepted, and
    # `--version` — which loads nothing — went on to check the ledger (w5/088).
    # It loads first because the helper drops a load cache that an attachment
    # appearing or vanishing has made stale, which bean-check would trust (w5/116);
    # its own finding still waits for bean-check to accept the ledger.
    portable: BeaError | None = None
    root_hint: str | None = None
    if not _INFORMATIONAL & set(args):
        try:
            loaded = launch.helper_json(["check", "--file", str(file), "--documents-only"])
        except BeaError as error:
            if str(error).startswith(_UNDECODABLE):
                # bean-check reports a file that is not UTF-8 as a codec message
                # at a line; the helper names the file, the byte and the remedy,
                # and no bean-check option makes those bytes decode (w5/278).
                raise
            portable = error
        else:
            root_hint = loaded.get("root_hint")
            failed = [str(line) for line in loaded.get("plugin_failures") or []]
            if failed and not current.debug:
                # bean-check reports a plugin that cannot load as a traceback at
                # `<load>:0`; the helper names the directive's file and line, as
                # `--json check` and every other read do. The other load errors
                # are listed only when no option could have changed them (w5/256).
                if args:
                    raise LedgerError(f"{file}: {len(failed)} plugin(s) failed to load.", details=failed)
                errors = [str(line) for line in loaded.get("errors") or failed]
                raise LedgerError(f"{file}: {len(errors)} error(s).", details=errors)
            if not args and loaded.get("clean"):
                # That load ran bean-check's own loader and validations and found
                # nothing, and bean-check prints nothing for a clean ledger: a
                # native run would only load it again, every plugin twice (w5/430).
                # Errors still come from bean-check, in its own words.
                raise typer.Exit(0)
    code = launch.run_native("bean-check", [*isolate, str(file), *args], ledger=file)
    if code != 0:
        # An included leaf fails on accounts its root opens; say which root
        # to check instead (w5/348).
        if root_hint:
            output.note(root_hint)
        raise typer.Exit(code)
    if portable is not None:
        raise portable
    raise typer.Exit(0)


#: bean-check options that print and exit without reading the ledger.
_INFORMATIONAL = frozenset({"--version", "--help", "-h"})

#: How `cli.utils.decode_error_message` and its engine twin open their refusal.
_UNDECODABLE = "Cannot decode '"


_CACHE_FLAG = "--cache-filename"


def _enables_auto(args: list[str]) -> bool:
    """Whether bean-check will read `--auto` / `-a` from these arguments, clustered or not."""
    index = 0
    while index < len(args) and args[index] != "--":
        arg = args[index]
        if arg == _CACHE_FLAG:
            index += 1  # its value, whatever it looks like
        elif arg == "--auto" or (arg.startswith("-") and not arg.startswith("--") and "a" in arg):
            return True
        index += 1
    return False


def _disables_cache(args: list[str]) -> bool:
    """Whether bean-check will read `--no-cache` / `-C` from these arguments, clustered or not."""
    index = 0
    while index < len(args) and args[index] != "--":
        arg = args[index]
        if arg == _CACHE_FLAG:
            index += 1  # its value, whatever it looks like
        elif arg == "--no-cache" or (arg.startswith("-") and not arg.startswith("--") and "C" in arg):
            return True
        index += 1
    return False


def _names_cache_file(args: list[str]) -> bool:
    return _without_cache_file(args) != args


def _without_cache_file(args: list[str]) -> list[str]:
    """The arguments without `--cache-filename` and its value, before any `--`."""
    kept: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--":
            kept.extend(args[index:])
            break
        if arg == _CACHE_FLAG:
            index += 2
            continue
        if not arg.startswith(f"{_CACHE_FLAG}="):
            kept.append(arg)
        index += 1
    return kept


def _refuse_cache_over_ledger(file: Path, args: list[str]) -> None:
    """Apply the load-cache guard to `--cache-filename`, last one winning as upstream reads it.

    `--no-cache` removes the cache path unconditionally, so the guard holds
    with or without it; the environment default applies when no flag is given.
    """
    pattern = None
    index = 0
    while index < len(args) and args[index] != "--":
        if args[index] == _CACHE_FLAG and index + 1 < len(args):
            pattern = args[index + 1]
            index += 1
        elif args[index].startswith(f"{_CACHE_FLAG}="):
            pattern = args[index].split("=", 1)[1]
        index += 1
    output.refuse_cache_over_ledger(file, pattern, _CACHE_FLAG)


def _closure_needs_compat(file: Path) -> tuple[str, str] | None:
    """Why the closure must skip native bean-check, or None when it can run it.

    A BOM-marked file fails upstream outright, mixed Unicode normalizations
    read as distinct accounts there, and URL includes cannot be fetched; the
    helper reads all three shapes. Pure NFC unmarked local closures keep
    native output byte for byte. Answers the reason plus what to do instead.
    """
    from cli.utils import has_bom

    try:
        members = output.ledger_closure(file)
    except OSError:
        return None
    marked = [str(member) for member in members if has_bom(member)]
    if marked:
        # Bare `bea format -i` reads stdin and is refused, so the remedy names
        # every marked file: one run of the printed command clears the closure (w5/197).
        return (
            "a file in its include closure starts with a UTF-8 BOM bean-check cannot parse",
            f"Run {shlex.join(['bea', 'format', '-i', *marked])} to strip the mark, then retry.",
        )
    for member in members:
        try:
            raw = member.read_bytes()
        except OSError:
            continue
        text = raw.decode("utf-8", errors="ignore")
        if not unicodedata.is_normalized("NFC", _PROSE_RE.sub("", text)):
            # format -i never renormalizes existing bytes, so it is no remedy here.
            return (
                f"{member} names an account or tag outside Unicode NFC, which bean-check reads "
                "as distinct from its NFC spelling",
                "Drop the bean-check options to check through the helper, "
                "or re-save the file in Unicode NFC, then retry.",
            )
        if _URL_INCLUDE_RE.search(text):
            return (
                "a file in its include closure names a URL include native bean-check cannot fetch",
                "Run without extra options to check through the helper.",
            )
    return None
