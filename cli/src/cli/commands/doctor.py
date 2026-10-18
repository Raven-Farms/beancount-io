"""`bea doctor` — delegate to upstream `bean-doctor` in the engine environment."""

from __future__ import annotations

import contextlib
import errno
import os
import re
import shlex
import subprocess
import sys
import unicodedata
from pathlib import Path

import typer

from cli import output
from cli.config import DEFAULT_ENTRY_FILE_FALLBACKS
from cli.context import refuse_expanding_ledger_path
from cli.engine import launch
from cli.errors import (
    AuthError,
    BeaError,
    ConflictError,
    LedgerError,
    UsageError,
    refuse_json,
    refuse_misplaced_global,
)
from cli.native_command import ForwardingCommand
from cli.native_help import native_help, native_options
from cli.utils import decode_error_message, has_bom

doctor_app = typer.Typer(
    name="doctor",
    help=(
        "Beancount diagnostics (delegates to bean-doctor). Operations take the ledger file as a "
        "positional argument; --file, BEA_FILE, and ./main.bean do not apply."
    ),
    no_args_is_help=True,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)

_OPS = (
    "lex",
    "parse",
    "roundtrip",
    "directories",
    "list-options",
    "print-options",
    "context",
    "linked",
    "region",
    "missing-open",
    "display-context",
)


#: Native options on these operations that consume the following argument.
#: Upstream's `region` has exactly one and neither `context` nor `linked` has
#: any; there are no boolean flags, and `--name=value` carries its own value.
#: Taken from `beancount.scripts.doctor`, which the frontend may not import —
#: `tests/test_doctor_option_placement.py` pins that this still matches it.
_VALUE_OPTIONS = frozenset({"--conversion"})


def _operand_indices(args: list[str]) -> list[int]:
    """Where the native operands sit in a forwarded argv.

    Options may appear anywhere Click accepts them, so operands cannot be read
    by position. Skipping only arguments that start with `-` left an option's
    *value* looking like an operand: `doctor region BOOKS --conversion cost
    LOC` read `--conversion` as the location, so the location kept no
    resolution, and named `cost` as the region in the empty-scope message.
    """
    indices: list[int] = []
    index = 0
    length = len(args)
    while index < length:
        value = args[index]
        if value == "--":  # Everything after it is an operand by definition.
            indices.extend(range(index + 1, length))
            break
        if value.startswith("-"):
            index += 2 if value in _VALUE_OPTIONS else 1
            continue
        indices.append(index)
        index += 1
    return indices


def _positionals(args: list[str]) -> list[str]:
    """The operands bean-doctor will see, in order."""
    return [args[index] for index in _operand_indices(args)]


def _refuse_directory_ledger(op: str, args: list[str]) -> None:
    """Refuse a directory where the operation expects its ledger file.

    Upstream's ledger argument accepts any existing path, so a directory got as
    far as `open()` and came back as a raw `IsADirectoryError` traceback with
    exit 1 (w5/138). Said here the way `--file DIRECTORY` is said everywhere
    else. `list-options` takes no ledger; its stray operand is upstream's to
    reject.
    """
    positionals = _positionals(args)
    if op == "list-options" or not positionals:
        return
    if not positionals[0].strip():
        # `Path('')` is the working directory, so `doctor lex ''` was refused
        # as a directory it was never given (w5/387).
        raise UsageError(f"The ledger path for bea doctor {op} is empty; name the ledger file.")
    ledger = Path(positionals[0])
    if not ledger.is_dir():
        if os.path.lexists(ledger) and not ledger.is_file():
            # `<(…)` names a pipe this process holds; upstream, which cannot
            # open it, said the path "does not exist" (w5/436).
            raise UsageError(f"Ledger path {output.not_a_file(ledger)}. Save it to a file and pass that file.")
        return
    hint = next(
        (ledger / name for name in DEFAULT_ENTRY_FILE_FALLBACKS if (ledger / name).is_file()),
        ledger / DEFAULT_ENTRY_FILE_FALLBACKS[0],
    )
    # Every other operand and option stays: `context DIR 3` suggested
    # `context DIR/main.bean`, which upstream refused for its LOCATION (w5/344).
    rebuilt = list(args)
    rebuilt[_operand_indices(args)[0]] = str(hint)
    raise UsageError(
        f"Ledger path '{ledger}' is a directory; expected a ledger file. "
        f"Pass its root ledger instead, for example {shlex.join(['bea', 'doctor', op, *rebuilt])}."
    )


# `context` and `linked` take `FILENAME LOCATION`; `region` takes
# `FILENAME REGION`, which may also carry a filename. All three resolve that
# filename the same way, and get it wrong the same way.
_LOCATED_OPS = frozenset({"context", "linked", "region"})


def _located_against_ledger(op: str, args: list[str]) -> list[str]:
    """Resolve a relative location filename against the ledger it belongs to.

    `bean-doctor` resolves it against the process working directory, so
    `doctor context /abs/books/main.bean txns/jan.bean:4` only works from inside
    the books tree — even though `txns/jan.bean` is exactly how the ledger's own
    `include` spells that file. When the working directory has no such file but
    the root ledger's directory does, that is the file meant.

    A location that already resolves is passed through untouched, so this only
    ever turns a guaranteed failure into an answer.
    """
    if op not in _LOCATED_OPS:
        return args
    # These operations take exactly `FILENAME LOCATION`, so read the operands
    # rather than assuming the location follows the ledger: an option between
    # them is valid Click and used to defeat this entirely.
    operands = _operand_indices(args)
    if len(operands) < 2:
        return args
    ledger = Path(args[operands[0]]).expanduser()
    if not ledger.is_file():
        return args
    position = operands[1]
    # Upstream's own split: the filename is everything before the trailing
    # line fields, so a colon inside it (`tx:jan.bean:1`) belongs to the name.
    # `linked` takes a line or, like `region`, a `start:end` range; the
    # range form was read as file `jan.bean:1` and left unresolved (w5/494).
    forms = [r"\d+:\d+"] if op == "region" else [r"\d+:\d+", r"\d+"] if op == "linked" else [r"\d+"]
    for lines in forms:
        match = re.fullmatch(rf"(.+):({lines})", args[position])
        if match is None:
            continue
        head, rest = match.groups()
        if Path(head).is_absolute() or Path(head).exists():
            return args
        candidate = ledger.parent / head
        if candidate.exists():
            args = list(args)
            args[position] = f"{candidate}:{rest}"
            return args
    return args


def _syntax_errors_of(filename: str) -> list[str]:
    """Syntax errors in one file, or [] when the file cannot be checked here.

    A name that is not a readable file is upstream's to report, and a dead
    engine must not take the diagnostics tool down with it: both fail open to
    the plain passthrough.
    """
    if not Path(filename).is_file():
        return []
    try:
        data = launch.helper_json(["syntax", filename])
    except BeaError:
        return []
    return [str(error) for error in data.get("files", {}).get(filename, [])]


#: Operations that never load the ledger: `lex` and `parse` trace the named
#: file's tokens, and `list-options` takes no ledger at all.
_NON_LOADING_OPS = frozenset({"lex", "parse", "list-options"})


def _refuse_undecodable(ledger: str) -> None:
    """Refuse a ledger the loader cannot decode, as every read does (w5/278).

    Upstream logs the parser's `UnicodeDecodeError` and carries on, so
    `missing-open` and `context` exited 0 with nothing to say and
    `print-options` relayed the class name (w5/440). Only a file that fails
    to decode is checked further, and only an error the parser reports is
    refused: a byte outside UTF-8 in a comment loads as it always did.
    """
    root = Path(ledger)
    if not root.is_file():
        return
    for member in output.ledger_closure(root):
        if output.is_encrypted(member):
            continue
        try:
            member.read_bytes().decode("utf-8")
        except OSError:
            continue
        except UnicodeDecodeError as exc:
            if any("UnicodeDecodeError:" in error for error in _syntax_errors_of(str(member))):
                raise LedgerError(decode_error_message(member, exc)) from exc


_PLUGIN_DIRECTIVE = re.compile(rb"^plugin[ \t]", re.MULTILINE)
#: How `bea check` words a plugin that cannot be imported or crashes.
_PLUGIN_FAILURES = ('Cannot import plugin "', '" failed while running: ')


def _refuse_plugin_failures(op: str, ledger: str) -> None:
    """Refuse a ledger whose plugin cannot be imported or crashes, in check's one-line form.

    Upstream logs the traceback and carries on without the plugin, so
    `roundtrip` printed it and then "Congratulations" with exit 0, and
    `missing-open` answered for entries the plugin never ran on (w5/439).
    Only a closure that declares a plugin pays for the check load.
    """
    root = Path(ledger)
    if not root.is_file():
        return
    declared = False
    for member in output.ledger_closure(root):
        if output.is_encrypted(member):
            continue
        with contextlib.suppress(OSError):
            declared = declared or bool(_PLUGIN_DIRECTIVE.search(member.read_bytes()))
    if not declared:
        return
    try:
        launch.helper_json(["check", "--file", ledger])
    except BeaError as exc:
        failures = [line for line in exc.details if any(mark in line for mark in _PLUGIN_FAILURES)]
        if failures:
            raise LedgerError(f"doctor {op} cannot load {ledger}: {failures[0]}", details=failures[1:]) from None


def _closure_syntax_errors_of(filename: str) -> list[str]:
    """Syntax errors anywhere in the ledger's include closure, root first.

    `print-options` and `roundtrip` load the whole ledger, so an unparseable
    include fails them just as surely as an unparseable root: the loader logs
    the error and carries on with whatever it recovered. `lex` and `parse`
    read only the named file upstream, and keep using `_syntax_errors_of`.
    Fails open exactly like that helper does.
    """
    root = Path(filename)
    if not root.is_file():
        return []
    # An encrypted include is decrypted by the loader, never parsed as text (w5/495).
    members = [str(member) for member in output.ledger_closure(root) if not output.is_encrypted(member)]
    try:
        data = launch.helper_json(["syntax", *members])
    except BeaError:
        return []
    files = data.get("files", {})
    return [str(error) for member in members for error in files.get(member, [])]


#: String literals, `;` comments and org-mode headings never name an account,
#: so their normalization cannot split one; `bea check` routes on the same rule.
_PROSE_RE = re.compile(r'"(?:[^"\\]|\\.)*"|;[^\n]*|^\*[^\n]*', re.MULTILINE)

#: Operations upstream runs on the named file alone; the rest load its includes.
_SINGLE_FILE_OPS = frozenset({"lex", "parse"})

#: A managed price include, which only the helper's load resolves (w5/286).
_MANAGED_INCLUDE_RE = re.compile(r'^\s*include\s*"https?://', re.MULTILINE | re.IGNORECASE)


def _needs_compat(op: str, args: list[str]) -> bool:
    """Whether stock `bean-doctor` would misread what this operation reads.

    Upstream lexes a UTF-8 BOM as an error token glued to the first directive
    and keeps NFC and NFD spellings of one account apart, so on a ledger
    `bea check` accepts it printed default options and an `open` for an
    account already open, all with exit 0 (w5/135). The helper reads both
    shapes as the rest of `bea` does. Any other ledger keeps the upstream
    executable, and its output byte for byte.

    Upstream also reads a managed price include as a file glob that matches
    nothing, so an operation that loads the ledger saw none of the prices
    `balance` values a holding with (w5/286). The helper resolves it.
    """
    positionals = _positionals(args)
    if not positionals:
        return False
    root = Path(positionals[0]).expanduser()
    if not root.is_file():
        return False
    # Upstream resolves the ledger path's symlinks: its entries carried the
    # real path, so a location under a linked folder matched nothing, and a
    # linked root file read the includes beside its target. The helper loads
    # the path as named, as `check` and `list` do (w5/568).
    if op not in _SINGLE_FILE_OPS and os.path.realpath(root) != os.path.abspath(root):
        return True
    try:
        members = [root] if op in _SINGLE_FILE_OPS else output.ledger_closure(root)
    except OSError:
        return False
    for member in members:
        if output.is_encrypted(member):
            continue
        if has_bom(member):
            return True
        try:
            text = member.read_bytes().decode("utf-8", errors="ignore")
        except OSError:
            continue
        if not unicodedata.is_normalized("NFC", _PROSE_RE.sub("", text)):
            return True
        if op not in _SINGLE_FILE_OPS and _MANAGED_INCLUDE_RE.search(text):
            return True
    return False


def _run(op: str, args: list[str]) -> int:
    """Run one operation with the streams inherited, where it reads the ledger right."""
    if _needs_compat(op, args):
        return launch.run_engine_argv(["scoped", op, *args])
    return launch.run_native("bean-doctor", [op, *args], ledger=_ledger_operand(args))


def _capture(op: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    """`_run`, keeping the output for an operation that has to read its own answer."""
    if _needs_compat(op, args):
        return launch.capture_engine(["scoped", op, *args])
    return launch.capture_native("bean-doctor", [op, *args], ledger=_ledger_operand(args))


def _ledger_operand(args: list[str]) -> str | None:
    """The ledger an operation reads — upstream's first operand — whose load cache `bea` places."""
    positionals = _positionals(args)
    return positionals[0] if positionals else None


def _refuse_json() -> None:
    """Doctor has no JSON output; every operation says so the same way."""
    refuse_json(
        "doctor",
        hint="Run without --json and pass the ledger path as a positional argument.",
    )


def _replayed(completed: subprocess.CompletedProcess[str]) -> subprocess.CompletedProcess[str]:
    """Replay captured upstream output, passing a nonzero status straight through.

    Except a death on a signal, which is reported as the streamed operations
    report one rather than leaving the shell an undocumented status.
    """
    _replay(completed)
    code = launch.captured_status(completed)
    if code != 0:
        raise typer.Exit(code)
    return completed


def _forward(op: str, ctx: typer.Context) -> None:
    """Pass remaining argv through to bean-doctor, resolving a relative location."""
    _refuse_json()
    args = _located_against_ledger(op, list(ctx.args))
    operands = _positionals(args)
    if op == "context" and len(operands) >= 2:
        filename = Path(operands[1].rsplit(":", 1)[0])
        if output.is_encrypted(filename):
            raise UsageError(
                f"doctor context cannot inspect a location inside encrypted file '{filename}': "
                "Beancount decrypts it only while loading. Choose a location in a plaintext ledger file."
            )
    code = _run(op, args)
    raise typer.Exit(code)


def _replay(completed: subprocess.CompletedProcess[str]) -> None:
    """Print captured upstream output back to its own streams, verbatim."""
    output.utf8_stdout()
    output.replay(completed.stdout, sys.stdout)
    output.replay(completed.stderr, sys.stderr)
    # A failure line follows on stderr; flush first so redirected streams keep
    # upstream's output ahead of the error that refers to it.
    for stream in (sys.stdout, sys.stderr):
        if stream is not None:  # A closed descriptor (`>&-`) holds nothing to flush.
            stream.flush()


def _forward_parse(op: str, ctx: typer.Context) -> None:
    """Trace the parse, but exit 1 when recovery ran on unparseable input."""
    _refuse_json()
    args = list(ctx.args)
    positionals = _positionals(args)
    errors = _syntax_errors_of(positionals[0]) if positionals else []
    code = _run(op, args)
    if code == 0 and errors:
        raise LedgerError(f"doctor {op} recovered from syntax errors in {positionals[0]} (see above).")
    raise typer.Exit(code)


def _forward_print_options(ctx: typer.Context) -> None:
    """Refuse to print default options for a file that did not load."""
    _refuse_json()
    args = list(ctx.args)
    positionals = _positionals(args)
    if positionals:
        errors = _closure_syntax_errors_of(positionals[0])
        if errors:
            raise LedgerError(f"doctor print-options cannot load {positionals[0]}: {errors[0]}")
    code = _run("print-options", args)
    raise typer.Exit(code)


def _roundtrip_artifacts(ledger: str) -> list[Path]:
    """The two scratch files upstream's `roundtrip` writes beside the ledger.

    Derived exactly as `beancount.scripts.doctor.roundtrip` does —
    `os.path.splitext` then `<base>.roundtrip1<ext>` — because the refusal
    below is only worth as much as its agreement with upstream. Upstream's
    `ledger_path` is `click.Path(resolve_path=True)`, so a symlinked ledger is
    resolved first and the scratch files land beside its target (w1/156).
    """
    base, extension = os.path.splitext(os.path.realpath(ledger))
    return [Path(f"{base}.roundtrip{index}{extension}") for index in (1, 2)]


def _refuse_roundtrip_collisions(ledger: str) -> None:
    """Refuse when the diagnostic's scratch names already belong to someone.

    Upstream opens both with `w` and removes them in a `finally`, unconditionally.
    So a file already at one of those paths is overwritten and then deleted —
    a read-only diagnostic that reported `Entries are the same. Congratulations.`
    while destroying a ledger include sitting beside the file it was checking.

    `bea` cannot make upstream pick other names, so it refuses rather than let
    that happen, and refuses before *either* forwarding branch can run.

    `lexists`, not `exists`: a dangling symlink is not an absent file here,
    because opening it for write would create its target and the cleanup would
    then remove it.
    """
    taken = [path for path in _roundtrip_artifacts(ledger) if os.path.lexists(path)]
    if not taken:
        return
    named = ", ".join(str(path) for path in taken)
    raise ConflictError(
        f"doctor roundtrip would overwrite and then delete {named}; nothing was run.",
        details=[
            "Upstream writes its comparison to those exact names and removes them afterwards.",
            "Move or rename them, then run the diagnostic again.",
        ],
    )


def _load_cache_of(filename: Path) -> Path | None:
    """Where Beancount keeps the load cache of an absolute `filename`.

    Derived as `beancount.loader.get_cache_filename` does from the pattern the
    child runs with — `BEANCOUNT_LOAD_CACHE_FILENAME`, or `bea`'s own place
    under the cache home: relative to the file's directory unless absolute,
    with `{filename}` standing for the base name.
    """
    pattern = launch.load_cache_pattern(filename)
    try:
        return Path(os.path.join(filename.parent, pattern).format(filename=filename.name))
    except (IndexError, KeyError, ValueError):
        return None


def _roundtrip_load_cache(ledger: str) -> Path | None:
    """The load cache upstream's `roundtrip` leaves behind for its first scratch file.

    Upstream reads `<stem>.roundtrip1<suffix>` back through the cached loader
    and removes only the two scratch files, so a ledger slow enough to be
    cached kept a hidden cache of a file that no longer existed, about three
    times the ledger's size (w5/118). Switching the cache off for the child is
    no answer: Beancount then deletes the ledger's own cache.

    None when a pattern without `{filename}` gives the scratch file the
    ledger's own cache path, which is not this command's to remove.
    """
    cache = _load_cache_of(_roundtrip_artifacts(ledger)[0])
    return None if cache == _load_cache_of(Path(os.path.realpath(ledger))) else cache


def _signature(path: Path | None) -> tuple[int, int, int] | None:
    """What tells a file this run wrote from one that was already there; None when absent."""
    if path is None:
        return None
    try:
        found = path.lstat()
    except OSError:
        return None
    return (found.st_ino, found.st_mtime_ns, found.st_size)


def _private_roundtrip_artifacts(ledger: str) -> list[Path]:
    """Create upstream's two scratch names first, private, and return the ones created.

    Upstream writes a full printed copy of the ledger to each with the process
    umask, so a `0600` ledger was copied out world-readable for the length of
    the run (w5/457). Its `open(..., "w")` truncates an existing file and keeps
    that file's mode. The collision refusal has already run, so whatever is at
    these names afterwards is this run's to remove.
    """
    created: list[Path] = []
    for path in _roundtrip_artifacts(ledger):
        try:
            os.close(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
        except OSError as exc:
            if exc.errno in (errno.EACCES, errno.EPERM, errno.EROFS):
                # Upstream raised, then crashed in its own cleanup: a 34-line
                # double traceback, exit 1 (w5/572). A permission failure is 3.
                for made in created:
                    made.unlink(missing_ok=True)
                raise AuthError(
                    f"doctor roundtrip writes scratch copies beside the ledger, and {path.parent} is not "
                    "writable. Nothing was written."
                ) from None
            continue
        created.append(path)
    return created


def _forward_roundtrip(ctx: typer.Context) -> None:
    """Compare entry sets, without congratulations on unparseable input."""
    _refuse_json()
    args = list(ctx.args)
    positionals = _positionals(args)
    if positionals:
        _refuse_roundtrip_collisions(positionals[0])
    errors = _closure_syntax_errors_of(positionals[0]) if positionals else []
    scratch_cache = _roundtrip_load_cache(positionals[0]) if positionals else None
    before = _signature(scratch_cache)
    scratch = _private_roundtrip_artifacts(positionals[0]) if positionals else []
    try:
        completed = _capture("roundtrip", args)
    finally:
        # Upstream removes only the copies it got as far as writing.
        for path in scratch:
            with contextlib.suppress(OSError):
                path.unlink()
    if scratch_cache is not None and _signature(scratch_cache) not in (None, before):
        with contextlib.suppress(OSError):
            scratch_cache.unlink()
    if errors:
        _replay_without_congratulations(completed)
        raise LedgerError(f"doctor roundtrip cannot compare {positionals[0]}: {errors[0]}")
    # Captured rather than streamed so the verdict can be read: upstream logs
    # `Entries differ!` and returns 0 regardless, so a real failed comparison
    # exited 0 and nothing automated could tell it from a clean one.
    _replayed(completed)
    if _entries_differ(completed.stderr):
        raise LedgerError(
            f"doctor roundtrip found that {positionals[0]} does not survive a print/parse cycle (see above).",
        )
    raise typer.Exit(0)


def _entries_differ(stderr: str) -> bool:
    """Whether upstream's comparison reported a mismatch.

    Read from stderr alone, and never stdout: upstream logs its verdict but
    *prints* the differing entries, so a narration quoting this very phrase
    would otherwise be mistaken for the diagnostic's own conclusion.
    """
    return any("Entries differ!" in line for line in stderr.splitlines())


def _replay_without_congratulations(completed: subprocess.CompletedProcess[str]) -> None:
    """Upstream's trace minus its success copy, which the errors above belie."""
    for text, stream in ((completed.stdout, sys.stdout), (completed.stderr, sys.stderr)):
        kept = "".join(line for line in text.splitlines(keepends=True) if "Congratulations" not in line)
        output.replay(kept, stream)


def _forward_directories(ctx: typer.Context) -> None:
    """Map upstream's ERROR lines to the exit status gates need."""
    _refuse_json()
    args = list(ctx.args)
    completed = _replayed(_capture("directories", args))
    problems = [
        line
        for stream in (completed.stdout, completed.stderr)
        for line in stream.splitlines()
        if line.startswith("ERROR:")
    ]
    if problems:
        noun = "directory" if len(problems) == 1 else "directories"
        raise LedgerError(f"doctor directories found {len(problems)} invalid {noun} (see above).")
    raise typer.Exit(0)


def _refuse_partial_load(op: str, ledger: str) -> None:
    """Refuse an answer that would silently leave out what a syntax error hid.

    The loader skips an unparseable directive and carries on, so
    `missing-open` listed the opens of the entries it could parse with exit
    0, and `linked` showed half a link group (w5/596). Refused before any
    output: `missing-open main.bean >> main.bean` appends what it prints.
    """
    errors = _closure_syntax_errors_of(ledger)
    if errors:
        raise LedgerError(f"doctor {op} cannot load {ledger}: {errors[0]}", details=errors[1:])


def _forward_scoped(op: str, ctx: typer.Context) -> None:
    """Fail an empty link/region scope instead of printing a blank success."""
    _refuse_json()
    args = _located_against_ledger(op, list(ctx.args))
    located = _positionals(args)
    if located:
        _refuse_partial_load(op, located[0])
    # Through the helper rather than the `bean-doctor` script: same upstream
    # command, run where bea can number its balance tree from the entries in
    # scope instead of from the whole ledger's display context (w3/352).
    completed = _replayed(launch.capture_engine(["scoped", op, *args]))
    rest = [
        line
        for stream in (completed.stdout, completed.stderr)
        for line in stream.splitlines()
        if line.strip() and line.strip() != "Net Income: ()"
    ]
    if not rest:
        positionals = _positionals(args)
        scope = positionals[1] if len(positionals) > 1 else "?"
        ledger = positionals[0] if positionals else "?"
        raise LedgerError(f"doctor {op} matched no entries for '{scope}' in {ledger}.")
    raise typer.Exit(0)


def _forward_missing_open(ctx: typer.Context) -> None:
    """Print upstream's missing opens, then name the inactive ones it omits."""
    _refuse_json()
    args = list(ctx.args)
    positionals = _positionals(args)
    if positionals:
        _refuse_partial_load("missing-open", positionals[0])
    _replayed(_capture("missing-open", args))
    if not positionals:
        raise typer.Exit(0)
    try:
        launch.helper_json(["check", "--file", positionals[0]])
    except BeaError as exc:
        details = exc.details or []
    else:
        details = []
    inactive = [line for line in details if "inactive account" in line]
    if inactive:
        # Beancount says "inactive" for a posting dated before the open as
        # well as after the close, and reports one line per posting. They are
        # the error's details, on stderr: stdout holds only the `open` lines,
        # which `missing-open main.bean >> main.bean` appends (w5/567).
        accounts = {line.split("inactive account '", 1)[1].split("'", 1)[0] for line in inactive if "'" in line}
        raise LedgerError(
            f"doctor missing-open found {len(inactive)} reference(s) to {len(accounts) or len(inactive)} "
            "inactive account(s) (posted before the open date or after the close); "
            "move the open earlier, reopen the account, or fix the postings.",
            details=inactive,
        )
    raise typer.Exit(0)


def _register(op: str) -> None:
    help_text = f"Run bean-doctor {op}."
    forwarder = {
        "lex": lambda ctx: _forward_parse("lex", ctx),
        "parse": lambda ctx: _forward_parse("parse", ctx),
        "roundtrip": _forward_roundtrip,
        "directories": _forward_directories,
        "print-options": _forward_print_options,
        "linked": lambda ctx: _forward_scoped("linked", ctx),
        "region": lambda ctx: _forward_scoped("region", ctx),
        "missing-open": _forward_missing_open,
    }.get(op)
    if forwarder is None:

        def forwarder(ctx: typer.Context, op: str = op) -> None:
            _forward(op, ctx)

    @doctor_app.command(
        op,
        cls=ForwardingCommand,
        help=help_text,
        epilog=native_help(f"doctor {op}"),
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    )
    def _cmd(ctx: typer.Context) -> None:
        assert forwarder is not None
        refuse_misplaced_global(
            f"doctor {op}", list(ctx.args), native_options(f"doctor {op}"), reads="the ledger", json_output=False
        )
        _refuse_directory_ledger(op, list(ctx.args))
        # Every operation that loads its ledger starts upstream's loader, which
        # deletes an unreadable file at the cache path the environment names.
        positionals = _positionals(list(ctx.args))
        if positionals and Path(positionals[0]).is_file():
            output.refuse_cache_over_ledger(Path(positionals[0]))
        # Upstream's loader expands `$NAME` in the ledger path (w5/315).
        if positionals and op != "list-options":
            refuse_expanding_ledger_path(os.path.abspath(positionals[0]))
        if positionals and op not in _NON_LOADING_OPS:
            ledger = Path(positionals[0])
            if output.has_unreadable_include(ledger) or output.has_duplicate_member(ledger):
                # Upstream answers an include it cannot open with a traceback;
                # the helper names the include and its includer, as every
                # read does (w5/120, w5/438). Upstream also loads one file
                # reached under two names twice, counting it twice, where the
                # helper refuses with `Duplicate include` (w5/433, w5/569).
                launch.helper_json(["check", "--file", positionals[0]])
            _refuse_undecodable(positionals[0])
            _refuse_plugin_failures(op, positionals[0])
        forwarder(ctx)


for _op in _OPS:
    _register(_op)


@doctor_app.command(
    "dump-lexer",
    cls=ForwardingCommand,
    epilog=native_help("doctor dump-lexer"),
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def dump_lexer(ctx: typer.Context) -> None:
    """Alias for bean-doctor lex."""
    refuse_misplaced_global(
        "doctor dump-lexer", list(ctx.args), native_options("doctor dump-lexer"), reads="the ledger", json_output=False
    )
    _refuse_directory_ledger("dump-lexer", list(ctx.args))
    _forward_parse("lex", ctx)
