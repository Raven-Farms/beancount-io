"""`bea check` — native bean-check, with bea's JSON envelope via the helper."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import typer

from cli import context, output
from cli.engine import launch
from cli.errors import UsageError

_URL_INCLUDE_RE = re.compile(r'^\s*include\s+"https?://', re.MULTILINE)
"""An include line native bean-check cannot resolve (w1/m29).

A posting line can never match: account names cannot start with the lowercase
`include` keyword, and a `;` comment never has the keyword first. Close
enough to exact for routing the closure to the helper check.
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
    _refuse_cache_over_ledger(file, ctx.args)
    # bean-check keys its load cache on the files read, not on the plugin set,
    # and every later read trusts that cache. A load made with the auto plugins
    # must neither be stored there nor answered from a default load's entry (w5/111).
    isolate = ["--no-cache"] if _enables_auto(ctx.args) else []
    code = launch.run_native("bean-check", [*isolate, str(file), *ctx.args])
    if code != 0:
        raise typer.Exit(code)
    # bean-check does not cover document paths that resolve outside the ledger tree;
    # the helper check does, so copies that still resolve against another tree fail.
    # Only that rule: this second load knows none of bean-check's options, so
    # re-judging validity failed a ledger `--auto` had just accepted, and
    # `--version` — which loads nothing — went on to check the ledger (w5/088).
    if not _INFORMATIONAL & set(ctx.args):
        launch.helper_json(["check", "--file", str(file), "--documents-only"])
    raise typer.Exit(0)


#: bean-check options that print and exit without reading the ledger.
_INFORMATIONAL = frozenset({"--version", "--help", "-h"})


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

    strip_bom = "Run bea format -i to strip the mark, then retry."
    try:
        members = output.ledger_closure(file)
    except OSError:
        return None
    for member in members:
        if has_bom(member):
            return (
                "a file in its include closure starts with a UTF-8 BOM bean-check cannot parse",
                strip_bom,
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
