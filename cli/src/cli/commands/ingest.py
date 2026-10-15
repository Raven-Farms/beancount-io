"""`bea ingest` — run the user's Beangulp ingest script through the engine.

Identify, extract, and archive stay in Beangulp's own CLI (the script that
builds `Ingest(importers, hooks=...)`). This module only picks the engine
interpreter, requires `bea engine enable beangulp`, and forwards the subcommand.
`bea import` remains the review/apply workflow and is unchanged.
"""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path
from typing import Annotated

import typer

from cli import context, output
from cli.engine import launch
from cli.errors import UsageError, placement_hint, refuse_json
from cli.native_command import ForwardingCommand
from cli.native_help import native_help

_EXTRA = {"allow_extra_args": True, "ignore_unknown_options": True}
_CONFIG = Annotated[
    Path | None,
    typer.Option("--config", help="Ingest script (defaults to ingest.py beside the ledger or cwd)"),
]

ingest_app = typer.Typer(
    name="ingest",
    help=("Run Beangulp identify/extract/archive via your ingest script.\n\nRequires 'bea engine enable beangulp'."),
    no_args_is_help=True,
)


def _ingest_script(supplied: Path | None) -> Path:
    """Locate the user's ingest script: --config, else ingest.py beside the ledger or cwd.

    Made absolute without following links: Beangulp files `archive` documents
    beside the script path it was started with, so a symlinked `ingest.py`
    must stay the link, not become the shared script it points to.
    """
    if supplied is not None:
        return supplied.expanduser().absolute()
    try:
        ledger = context.current().entry_file()
    except UsageError:
        ledger = None
    candidates: list[Path] = []
    if ledger is not None:
        candidates.append(ledger.parent / "ingest.py")
    candidates.append(Path.cwd() / "ingest.py")
    for candidate in candidates:
        if candidate.is_file():
            return candidate.absolute()
    raise UsageError(
        "Choose an ingest script with --config FILE, or place ingest.py beside the root ledger "
        "(or in the current directory). The script should call beangulp.Ingest(...)()."
    )


#: Beangulp `extract`'s boolean short flags (`--reverse`, `--failfast`,
#: `--quiet`). Click lets them cluster in front of `-o`/`-e`, so `-qo X` names
#: a destination exactly as `-o X` does (w1/141).
_EXTRACT_FLAGS = "rxq"


def _forward(operation: str, ctx: typer.Context, config: Path | None) -> None:
    refuse_json("ingest", hint="Run without --json for native output; use bea import for a JSON preview.")
    if operation == "extract":
        # `archive -o DIR` moves source documents into a directory tree — not a
        # ledger write — so it stays outside the guard on purpose, and
        # `identify` writes nothing at all.
        output.guard_forwarded_output(list(ctx.args), _extract_ledgers(ctx), flags=_EXTRACT_FLAGS)
    script = _ingest_script(config)
    if operation == "extract":
        _refuse_output_over_inputs(list(ctx.args), script)
    _refuse_config_only_script(script)
    existing = (
        output.forwarded_option(list(ctx.args), "-e", "--existing", flags=_EXTRACT_FLAGS)
        if operation == "extract"
        else None
    )
    placed = {"ledger": os.path.abspath(os.path.expanduser(existing))} if existing else {}
    if placed and output.has_unreadable_include(Path(placed["ledger"])):
        # Beangulp loads `-e` with Beancount, which answers an include it
        # cannot open with a traceback; the helper names it (w5/120, w5/438).
        launch.helper_json(["check", "--file", placed["ledger"]])
    code = launch.run_optional_script("beangulp", script, [operation, *ctx.args], **placed)
    raise typer.Exit(code)


def _extract_ledgers(ctx: typer.Context) -> list[Path]:
    """The ledgers an `extract` must never write over: `bea --file`, and Beangulp's `-e`.

    Both are read by the run, so both are destinations that would destroy the
    books being extracted against.
    """
    ledgers: list[Path] = []
    try:
        ledgers.append(context.current().entry_file())
    except UsageError:
        pass
    existing = output.forwarded_option(list(ctx.args), "-e", "--existing", flags=_EXTRACT_FLAGS)
    if existing is not None:
        ledgers.append(Path(existing).expanduser())
    return ledgers


def _refuse_output_over_inputs(args: list[str], script: Path) -> None:
    """Refuse an extract destination that is a source document or the ingest script.

    Beangulp opens `-o` for writing once extraction is done, so a destination
    that is one of the run's own inputs replaced the bank export — the only
    evidence for the extracted entries — or the script, and exited 0. Compared
    by identity, so a symlink or hard link to an input counts, and a source
    directory covers every file Beangulp would walk inside it.
    """
    value = output.forwarded_option(args, "-o", "--output", flags=_EXTRACT_FLAGS)
    if value is None:
        return
    destination = Path(value).expanduser()
    if not destination.exists():
        return  # Nothing there to lose; `-o -` and a fresh file pass through.
    output.refuse_input_alias(destination, script)
    for source in _positional_sources(args):
        if source.is_dir():
            for directory, _, names in os.walk(source):
                for name in names:
                    output.refuse_input_alias(destination, Path(directory, name))
        else:
            output.refuse_input_alias(destination, source)


def _positional_sources(args: list[str]) -> list[Path]:
    """Every forwarded argument that may be a source document or directory.

    Read generously: an option's value is harmless to include — it is either
    the ledger, already refused, or not a file the destination could alias —
    while a source mistaken for an option value would escape the guard. Only
    the destination itself is left out, in the spellings `forwarded_option`
    reads.
    """
    sources: list[Path] = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--":
            sources.extend(Path(rest).expanduser() for rest in args[index + 1 :])
            break
        if arg == "--output" or re.fullmatch(rf"-[{_EXTRACT_FLAGS}]*o", arg):
            index += 2
            continue
        if not arg.startswith("-"):
            sources.append(Path(arg).expanduser())
        index += 1
    return sources


def _refuse_config_only_script(script: Path) -> None:
    """Refuse an import CONFIG module, which would otherwise exit 0 silently.

    A `CONFIG = [...]` module loads, ignores argv, and exits 0 with empty
    output — indistinguishable from success. That shape belongs to
    `bea import --config`; `bea ingest` needs a script whose `__main__`
    calls the Beangulp entrypoint. Anything else passes through untouched:
    only the known-silent shape is refused.

    The shape is read from the syntax tree, not the spelling: an annotated
    `CONFIG: list = [...]` is the same module, and a script with a `__main__`
    block runs something even when the `Ingest` call sits in a module it
    imports. A file Python cannot parse is left for Python to report.
    """
    try:
        text = script.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    if re.search(r"Ingest\s*\(", text):
        return
    try:
        body = ast.parse(text).body
    except (SyntaxError, ValueError):
        return
    if any(_binds_config(node) for node in body) and not any(_is_main_guard(node) for node in body):
        raise UsageError(
            f"{script} looks like a `bea import --config` module (CONFIG = [...]). "
            "`bea ingest` needs a script that calls beangulp.Ingest(...)(); "
            "run `bea import --config` for this file instead."
        )


def _binds_config(node: ast.stmt) -> bool:
    """Whether a module-level statement assigns `CONFIG`, annotated or not."""
    if isinstance(node, ast.Assign):
        targets = node.targets
    elif isinstance(node, ast.AnnAssign) and node.value is not None:
        targets = [node.target]
    else:
        return False
    return any(
        isinstance(name, ast.Name) and isinstance(name.ctx, ast.Store) and name.id == "CONFIG"
        for target in targets
        for name in ast.walk(target)
    )


def _is_main_guard(node: ast.stmt) -> bool:
    """Whether a module-level statement is `if __name__ == "__main__":`, either way round."""
    if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
        return False
    operands = [node.test.left, *node.test.comparators]
    return any(isinstance(operand, ast.Name) and operand.id == "__name__" for operand in operands) and any(
        isinstance(operand, ast.Constant) and operand.value == "__main__" for operand in operands
    )


@ingest_app.command("identify", cls=ForwardingCommand, epilog=native_help("ingest identify"), context_settings=_EXTRA)
def identify(ctx: typer.Context, config: _CONFIG = None) -> None:
    """Identify which importer matches each document (Beangulp identify)."""
    _forward("identify", ctx, config)


@ingest_app.command("extract", cls=ForwardingCommand, epilog=native_help("ingest extract"), context_settings=_EXTRA)
def extract(ctx: typer.Context, config: _CONFIG = None) -> None:
    """Extract raw entries from documents (Beangulp extract; not bea import --apply)."""
    _forward("extract", ctx, config)


@ingest_app.command("archive", cls=ForwardingCommand, epilog=native_help("ingest archive"), context_settings=_EXTRA)
def archive(ctx: typer.Context, config: _CONFIG = None) -> None:
    """File documents into the archive hierarchy (Beangulp archive)."""
    _refuse_ledger_after_overwrite(list(ctx.args))
    _forward("archive", ctx, config)


def _refuse_ledger_after_overwrite(args: list[str]) -> None:
    """`-f` after `ingest archive` is Beangulp's `--overwrite`, not bea's ledger.

    `bea ingest archive … -f main.bean` replaced documents already filed and
    offered the ledger as one more source to archive, with exit 0 (w5/413).
    """
    for index, arg in enumerate(args[:-1]):
        if arg == "--":
            return
        following = args[index + 1]
        if arg in ("-f", "--overwrite") and following.endswith((".bean", ".beancount")):
            raise UsageError(
                f"{arg} after ingest archive is Beangulp's --overwrite, which replaces documents already filed, "
                f"and {following} would be archived as a source. {placement_hint('-f')} Nothing was changed."
            )
