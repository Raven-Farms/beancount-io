"""BQL, engine-side: upstream's dispatch with bea's path and rendering fixes.

This is where `bea query` runs after ADR014 t005. The frontend has no Beanquery
and no shell subclass; it passes a ledger path and a query string across the
process boundary and renders whatever comes back.

Upstream owns everything that makes a query a query: parsing, the statement
dispatch that makes `PRINT` print directives rather than a `ROW(*)` table,
`.run` and the rest of the dot commands, and the interactive shell. The fixes
below need Beancount objects, which is why they live here and not in `bea`:

- **Exact paths.** Beanquery attaches a ledger through a `beancount:<path>` DSN
  that it hands to `urlparse`, so a `#` or `?` in a filename reads as a
  fragment or query marker and a *different* file gets loaded, silently. We
  load the resolved path ourselves and attach the entries to a pathless DSN.
- **Result precision.** Beanquery formats a column with the ledger's display
  context, which rounds a computed value to the precision of the inputs
  (`convert()` of eight decimal places came back with five) and raises
  `decimal.InvalidOperation` outright on a balance wider than twelve integer
  digits. `result_context` derives the precision from the values being
  rendered instead.
- **Directive exports.** The shared writer printer preserves negative custom
  values, small decimal metadata, string escapes and whole cost specifications
  so reloading an export does not silently change those values.
"""

from __future__ import annotations

import ast
import difflib
import json
import os
import re
import stat
import sys
import unicodedata
from collections.abc import Callable, Hashable, Iterator, Mapping
from contextlib import contextmanager
from decimal import Decimal, localcontext
from functools import cache, partial
from pathlib import Path
from typing import Any, TextIO, get_origin

from bea_engine import protocol, stopping

LEDGER_DSN = "beancount:"
"""A pathless beanquery DSN: the source attaches the entries handed to it instead of loading a file."""

# Table names that are also BQL keywords: unquoted FROM binds wrongly (accounts →
# postings) or is a syntax error (balances). Quote them before execute.
_RESERVED_TABLE_FROM = re.compile(r'(?i)\b(FROM|JOIN)\s+(?<!")(accounts|balances)\b(?!")')


def _code_mask(text: str, *, literals: bool = True) -> str:
    """The query with every string literal and comment blanked to spaces.

    `literals=False` blanks only the comments, for a caller asking whether any
    code is there at all rather than where the keywords are.

    Exactly as long as the input, so a match found in the mask has the offsets
    of the real thing. That is what lets the relation rewrite below see only
    code: searching the raw text rewrote the insides of literals, so a
    narration search for `transfer from accounts` became `transfer from
    "accounts"` and matched nothing, and a double-quoted literal with more
    words after `balances` became a syntax error.

    Blanking a literal whole — quotes included — also means an already-quoted
    relation is invisible here, which is the right answer: it needs no
    rewriting. BQL escapes a quote by doubling it and comments with `/* */`;
    it has no line-comment form, so `--`, `#` and a bare `;` are syntax errors
    rather than text to skip (probed against the parser, not assumed).
    """
    out: list[str] = []
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char in "'\"":
            end = index + 1
            while end < length:
                if text[end] == char:
                    if end + 1 < length and text[end + 1] == char:  # A doubled quote is content.
                        end += 2
                        continue
                    end += 1
                    break
                end += 1
            out.append(" " * (end - index) if literals else text[index:end])
            index = end
        elif text.startswith("/*", index):
            end = text.find("*/", index + 2)
            end = length if end == -1 else end + 2
            out.append(" " * (end - index))
            index = end
        else:
            out.append(char)
            index += 1
    return "".join(out)


def _refuse_statement_tail(query_string: str, ledger_errors: list[str] | None = None) -> None:
    """Refuse BQL text carrying more than one statement.

    Beanquery parses the first statement and silently drops whatever follows
    a `;` — even text that is not BQL at all — so `SELECT 1; SELECT 2` stored
    in a `query` directive, or typed at the prompt, answered half and exited 0.
    Separators are found in the code mask, so a `;` inside a literal or a
    comment does not count, and a trailing `;` is not a second statement: the
    same rules as the frontend's one-shot `_split_statements`. Nor is a
    fragment of only whitespace and comments, so `SELECT 1; /* note */` is one.
    """
    masked = _code_mask(query_string)
    uncommented = _code_mask(query_string, literals=False)
    statements = 0
    start = 0
    for index in [*(i for i, char in enumerate(masked) if char == ";"), len(masked)]:
        if uncommented[start:index].strip():
            statements += 1
        start = index + 1
    if statements > 1:
        raise protocol.UsageError(
            f"One BQL statement per query; got {statements}. Beanquery would run only the first.",
            details=["Split the statements into separate queries."],
            ledger_errors=ledger_errors,
        )


def _quote_reserved_tables(query_string: str) -> str:
    """Rewrite `FROM accounts|balances` to the quoted form discovery documents.

    Matched against the code mask and spliced back by offset, so the user's own
    text — literals, comments — is returned byte-for-byte.
    """
    masked = _code_mask(query_string)
    pieces: list[str] = []
    cursor = 0
    for match in _RESERVED_TABLE_FROM.finditer(masked):
        start, end = match.span(2)
        pieces.append(query_string[cursor:start])
        pieces.append(f'"{query_string[start:end]}"')
        cursor = end
    pieces.append(query_string[cursor:])
    return "".join(pieces)


def load(file: Path) -> dict[str, Any]:
    """Load exactly this ledger file, for attaching to a pathless connection."""
    from bea_engine import managed_load

    entries, errors, options = managed_load.load_file(str(file))
    return {"entries": entries, "errors": errors, "options": options}


def connect(file: Path) -> Any:
    """A beanquery connection on the exact ledger file, includes and load errors intact."""
    import beanquery

    return beanquery.connect(LEDGER_DSN, **load(file))


def rows_answer(
    file: Path, query_string: str, *, allow_errors: bool = False, numberify: bool = False
) -> dict[str, Any]:
    """Columns, rows and load errors for one query, as JSON the frontend renders.

    The rows are JSON-ready: amounts as strings, a lot keeping the acquisition
    date and label that tell it from another lot at the same price.
    """
    conn = connect(file)
    errors = _gate([format_error(error, ledger_file=file) for error in conn.errors], allow_errors, file)
    cursor = _executed(conn, query_string, conn.execute, errors, file=file)
    rows = cursor.fetchall() if cursor.description is not None else []
    description = cursor.description
    if numberify and description is not None:
        from beanquery.numberify import numberify_results

        description, rows = numberify_results(description, rows, result_context(rows).build())
    return {
        "columns": columns(description),
        "rows": [[protocol._jsonable(_public_value(value)) for value in row] for row in rows],
        "errors": errors,
    }


def text_answer(
    file: Path,
    query_string: str,
    *,
    output: Path | None = None,
    format: str = "text",
    numberify: bool = False,
    allow_errors: bool = False,
    spreadsheet_safe: bool = False,
) -> dict[str, Any]:
    """Upstream's own rendering of one query, plus the ledger's load errors.

    Dispatched through the shell rather than through a bare `execute`, which is
    what makes `PRINT` print directives and `.run NAME` run a stored query
    instead of both arriving as a `ROW(*)` table. The text comes back in the
    envelope rather than on stdout so that the frontend stays the only place
    that renders: `bea` decides whether a ledger with errors may answer at all,
    and it cannot unprint a table.
    """
    import io

    if output is not None:
        # Keep the approved target stable if the user's symlink is retargeted
        # while the query runs. The alias check below sees this same path.
        output = output.resolve()
    # The shell renders into a buffer and the destination is opened only once
    # the whole query has succeeded. Opening it before the load would truncate
    # a `-o` naming the ledger under read before the load saw a byte of it;
    # opening it before the *query*, which is what this used to do, truncated
    # whatever the last good export was the moment the query failed — against
    # `USAGE.md`'s "a failed query or write preserves an existing export" — and
    # left a partial file behind if a query failed mid-render.
    buffer = io.StringIO()
    # `show_errors=False`: the load errors travel in the envelope, and
    # upstream printing them to stderr too would report each one twice.
    shell = build_shell(file, buffer, format=format, numberify=numberify, show_errors=False)
    shell.spreadsheet_safe = spreadsheet_safe
    errors = _gate([format_error(error, ledger_file=file) for error in shell.context.errors], allow_errors, file)
    if output is not None:
        # Still before the query: refusing to write over the ledger being read
        # is a refusal, and a refusal has to happen before any work is done.
        _refuse_alias(output, file, shell.context)
    _replay_init(shell, buffer if output is not None else None)
    _executed(shell.context, query_string, shell.onecmd, errors, file=file)
    if output is not None:
        # Rendered whole, then swapped in atomically. w3/380 moved this past
        # the *query*; the write itself still had to become atomic.
        _export(shell, output, buffer.getvalue())
        # The export is the result; the frontend has nothing left to print.
        return {"text": "", "errors": errors}
    return {"text": buffer.getvalue(), "errors": errors}


def _loaded_files(root: Path, context: Any) -> list[Path]:
    """Every file this query reads, so none of them may be a destination.

    The loader records its whole include closure in `options["include"]`, which
    is the only complete answer: a child holding nothing but `option` lines,
    comments or further includes produces no entries at all, so deriving
    membership from `entries[].meta.filename` silently left it unprotected and
    `.output` truncated it. Entry filenames are still folded in as a
    belt-and-braces fallback for a connection that carries no options.
    """
    files = [root]
    includes = (getattr(context, "options", None) or {}).get("include") or ()
    files.extend(Path(name) for name in includes if name)
    table = context.tables.get("entries")
    entries = getattr(table, "entries", None) or ()
    for entry in entries:
        name = (getattr(entry, "meta", None) or {}).get("filename")
        if name:
            files.append(Path(name))
    return files


def same_file(left: Path, right: Path) -> bool:
    """True when two paths name one file, through symlinks and hard links alike."""
    try:
        first, second = left.stat(), right.stat()
        return (first.st_ino, first.st_dev) == (second.st_ino, second.st_dev)
    except OSError:
        pass
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return False


def _find_alias(destination: Path, root: Path, context: Any) -> Path | None:
    """The ledger file a destination would overwrite, or None when it is safe."""
    for member in _loaded_files(root, context):
        if same_file(destination, member):
            return member
    return None


def _claiming_include(destination: Path, root: Path) -> str | None:
    """The include pattern that would make a destination part of the ledger once written (w5/072)."""
    from bea_engine.ledger.write import LedgerSnapshot, _included_new_file

    try:
        target = destination.expanduser().resolve()
        patterns = LedgerSnapshot.capture(root).patterns
    except (OSError, protocol.UsageError):
        return None
    return next((pattern for pattern in patterns if _included_new_file(target, pattern)), None)


def _refuse_alias(destination: Path, root: Path, context: Any) -> None:
    """Fail a destination that is one of the files this query reads."""
    member = _find_alias(destination, root, context)
    if member is not None:
        raise protocol.UsageError(
            f"--output {destination} would overwrite the ledger it reads ({member}); choose a different destination."
        )
    pattern = _claiming_include(destination, root)
    if pattern is not None:
        raise protocol.UsageError(
            f"--output {destination} would become part of the ledger it reads: the include pattern {pattern} "
            "matches that path. Choose a destination outside the ledger's includes."
        )


def _redirect_output(shell: Any, arg: str, stream: TextIO, file: Path | None) -> None:
    """Protect loaded inputs and keep the current stream when redirection fails."""
    if arg and file is not None:
        member = _find_alias(Path(arg), file, shell.context)
        if member is not None:
            protocol.note(
                f"Refusing to write query output to {arg}: it is one of the ledger files under query ({member})."
            )
            return
        pattern = _claiming_include(Path(arg), file)
        if pattern is not None:
            protocol.note(
                f"Refusing to write query output to {arg}: the include pattern {pattern} would make it "
                "part of the ledger under query."
            )
            return
    try:
        destination = open(arg, "w", encoding="utf-8") if arg else stream
    except OSError as exc:
        protocol.note(f"Cannot write to {arg}: {exc.strerror or exc}.")
        return
    if shell.outfile is not stream:
        shell.outfile.close()
    shell.outfile = destination


def _native_shell(source: str, *, interactive: bool, format: str, numberify: bool, show_errors: bool) -> Any:
    """Upstream's `BQLShell` on a native source, with bea's input and exit-status guards.

    Sources and rendering stay upstream's. What changes is what upstream only
    prints: `.run` naming no stored query, and a statement tail Beanquery would
    drop, are usage errors here, so a one-shot exits 2 instead of 0 and an
    interactive session reports them and carries on. `.output` keeps refusing
    the files the source reads.
    """
    from urllib.parse import urlparse

    from beanquery.shell import BQLShell

    dsn = source if re.match("[a-z]{2,}:", source) else "beancount:" + source
    parts = urlparse(dsn)
    file = Path(parts.path) if parts.scheme in {"beancount", "csv"} and parts.path else None
    if parts.scheme in {"beancount", "csv"}:
        # Upstream records a missing root as one more load error and answers
        # from an empty database, which a one-shot exported with exit 0 (w5/249),
        # and opens a `csv:` path, or no path at all, into a traceback (w5/250).
        # The frontend refuses first; this is the path the loader really gets.
        kind = "ledger" if parts.scheme == "beancount" else "CSV"
        if file is None:
            raise protocol.UsageError(
                f"--source '{source}' names no file; pass a ledger path, beancount:<path> or csv:<path>."
            )
        if not file.exists():
            raise protocol.UsageError(f"No {kind} file at '{file}' (from --source).")
        if file.is_dir():
            raise protocol.UsageError(
                f"{kind[0].upper()}{kind[1:]} path '{file}' (from --source) is a directory; expected a {kind} file."
            )

    class GuardedShell(BQLShell):  # type: ignore[misc]
        source_file = file
        debug = False
        replaying_init = False
        ran_query = False

        def error(self, message: str) -> None:
            _shell_error(self, message, super().error)

        def do_output(self, arg: str) -> None:
            """Send output to FILE or restore stdout, preserving source files."""
            _redirect_output(self, arg, sys.stdout, file)

        def do_help(self, arg: str) -> None:
            """List commands, writing to outfile like every other command."""
            _help_to_outfile(self, super().do_help, arg)

        def do_parse(self, arg: str) -> None:
            """Print the parsed sexp to outfile (not process stdout)."""
            print(self.parse(arg).tosexp(), file=self.outfile)

        def do_reload(self, arg: Any = None) -> None:
            """Reload the Beancount input file."""
            # Upstream loads the source itself; a Ctrl-C mid-parse waits for it.
            with stopping.deferring_interrupt():
                super().do_reload(arg)

        def do_run(self, arg: str) -> None:
            """Run a named stored query, or list them; missing names are usage errors."""
            _run_stored(self, arg)

        def do_describe(self, arg: str) -> None:
            """Describe table or structured type."""
            _split_dot_arguments("describe", arg)
            super().do_describe(arg)

        def do_set(self, arg: str) -> None:
            """Set shell settings variables."""
            _split_dot_arguments("set", arg)
            super().do_set(arg)

        _printing = False

        def on_Print(self, statement: Any) -> Any:  # noqa: N802 - beanquery dispatch name
            # Upstream's PRINT runs through `on_Select` with the beancount
            # format; its rows are entries by construction.
            self._printing = True
            try:
                return super().on_Print(statement)
            finally:
                self._printing = False

        def on_Select(self, statement: Any) -> Any:  # noqa: N802 - beanquery dispatch name
            if self.settings.format != "beancount" or self._printing:
                return super().on_Select(statement)
            # Upstream's beancount renderer unpacks every row as a directive, so
            # a column SELECT failed inside it with a traceback; the `--file`
            # shell refuses it as a usage error, and so does this one (w5/293).
            from beanquery.shell import FORMATS

            cursor = self.context.execute(statement)
            description, rows = cursor.description, cursor.fetchall()
            _require_entries(description, rows)
            dcontext = self.context.options.get("dcontext", None)
            with self.output as out:
                return FORMATS["beancount"](description, rows, out, dcontext=dcontext, **self.settings.todict())

        def execute(self, query: Any, **kwargs: Any) -> Any:
            self.ran_query = True
            statement = query if isinstance(query, str) else ""
            if statement:
                _refuse_statement_tail(statement)
            context = None if self.interactive else self.context
            return _compiled(partial(super().execute, query, **kwargs), statement, list, context)

        def onecmd(self, line: str) -> Any:
            return _recovering(self, self._dispatch, line)

        def _dispatch(self, line: str) -> Any:
            # Upstream runs nothing for a line with no leading identifier — a
            # query opening with a comment, or a dash-leading string such as
            # `--output=main.bean` — and the one-shot then exited 0 with no
            # output. Hand it to the parser, which runs it or says why not.
            command_name, _, parsed = self.parseline(line)
            if parsed and not command_name:
                return self.execute(parsed)
            return super().onecmd(line)

    # Help topics come from the handler docstrings on this class (see PreciseShell).
    for name, handler in vars(GuardedShell).items():
        if name.startswith("on_") and handler.__doc__ is None:
            handler.__doc__ = getattr(BQLShell, name).__doc__
    # Load before replaying init commands, so .output sees the include closure.
    make = partial(_attach_native, GuardedShell, source, dsn, interactive, format, numberify, show_errors)
    return _with_line_editor(make) if interactive else make()


def _attach_native(
    shell_class: Any, source: str, dsn: str, interactive: bool, format: str, numberify: bool, show_errors: bool
) -> Any:
    """Open a native source, naming a bad source parameter as a usage error (w5/293).

    Upstream builds the source from the URI's query string straight into its
    reader: `csv:t.csv?header=true` passed `header` twice, `?encoding=bogus`
    an unknown codec, `?dialect=nope` an unknown dialect, and each escaped as a
    traceback with exit 1. `-m` on a `csv:` source then failed at the first
    query, because only a Beancount source carries display precision.
    """
    import csv

    try:
        shell = shell_class(dsn, sys.stdout, interactive, False, format, numberify, show_errors)
    except (TypeError, LookupError, csv.Error) as exc:
        raise protocol.UsageError(
            f"Cannot open --source '{source}': {exc}.",
            details=["Check the parameters after `?` in the source URI against the source type."],
        ) from None
    if numberify and shell.context.options.get("dcontext") is None:
        raise protocol.UsageError(
            "--numberify (-m) needs a Beancount ledger source: this --source carries no display precision."
        )
    return shell


def _with_line_editor(make: Callable[[], Any]) -> Any:
    """An interactive shell whose history is bea's to load and save (w5/235).

    Upstream's constructor loads `~/.config/beanquery/history` guarded only
    against a missing file and registers an unguarded write at exit. libedit
    refuses a history with no entries, which is exactly what that write left
    when nothing was typed, so one empty session crashed every later one before
    its first prompt. The constructor therefore runs without the line editor,
    which is then set up here as upstream does it, except that a history
    problem costs the history and one line rather than the session.
    """
    import atexit

    import beanquery.shell as upstream

    readline = upstream.readline
    upstream.readline = None
    try:
        shell = make()
    finally:
        upstream.readline = readline
    if readline is None:
        return shell
    if "libedit" in (readline.__doc__ or ""):
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")
    readline.set_completer_delims(" \t\n\"\\'`@$><=;|&{(")
    history = Path(upstream.HISTORY_FILENAME).expanduser()
    reason = None
    try:
        history.parent.mkdir(parents=True, exist_ok=True)
        # Python's own open names the real problem; libedit answers EPERM for
        # anything it could not load.
        history.open("rb").close()
    except FileNotFoundError:
        pass
    except OSError as exc:
        reason = exc.strerror or type(exc).__name__
    else:
        try:
            readline.read_history_file(history)
        except OSError:
            reason = "not a history the line editor can read"
    if reason is not None:
        protocol.note(f"Cannot load query history {history}: {reason}; starting with an empty history.")
    readline.set_history_length(2048)
    atexit.register(_save_history, readline, history, reason is None)
    return shell


def _save_history(readline: Any, history: Path, loaded: bool) -> None:
    """Save the session's history at exit, never leaving a file the next load refuses."""
    try:
        if readline.get_current_history_length():
            readline.write_history_file(history)
        elif loaded:
            # Written out, an empty history is the header-only file libedit
            # cannot load. A file that did not load is left for its owner.
            history.unlink(missing_ok=True)
    except OSError:
        if loaded:  # Otherwise the session already said so when it opened.
            protocol.note(f"Cannot save query history to {history}.")


def _replay_init(shell: Any, output: TextIO | None = None) -> None:
    """Replay Beanquery's init file, as `bean-query` does, once the source is loaded.

    Upstream replays it inside the shell's constructor, before the source is
    attached, so a guarded `.output` there could neither see the files it must
    not overwrite nor run at all. An explicit `--output` stream, set here once
    the init file is done, outranks an init-file `.output`.
    """
    from beanquery.shell import INIT_FILENAME

    default = shell.outfile
    init = Path(INIT_FILENAME).expanduser()
    if init.is_file():
        shell.replaying_init = True
        try:
            for line in init.read_text(encoding="utf-8").splitlines():
                shell.onecmd(line)
        finally:
            shell.replaying_init = False
    if output is not None:
        if shell.outfile is not default:
            shell.outfile.close()
        shell.outfile = output


def native_interactive(
    source: str,
    *,
    format: str = "text",
    output: Path | None = None,
    numberify: bool = False,
    show_errors: bool = True,
    debug: bool = False,
) -> None:
    """Native Beanquery sources and rendering, with bea's destination protection."""
    import warnings

    warnings.filterwarnings("always")
    shell = _native_shell(source, interactive=True, format=format, numberify=numberify, show_errors=show_errors)
    shell.debug = debug
    try:
        if output is not None:
            if shell.source_file is not None:
                _refuse_alias(output, shell.source_file, shell.context)
        _replay_init(shell, None if output is None else output.open("w", encoding="utf-8"))
        shell.cmdloop()
    finally:
        if shell.outfile is not sys.stdout:
            shell.outfile.close()


def native_one_shot(
    source: str,
    query_string: str,
    *,
    format: str = "text",
    output: Path | None = None,
    numberify: bool = False,
    show_errors: bool = True,
) -> None:
    """One native query, the way `bean-query SOURCE QUERY` runs it, with a truthful exit status.

    `bean-query` printed `error: query "x" not found` for a missing stored
    query and still exited 0, so automation could not tell an unavailable
    query from an empty answer. Here that failure raises, and the caller exits
    2. An `--output` export is written only after the query succeeds, so a
    refused query leaves an existing export as it was.
    """
    import io

    shell = _native_shell(source, interactive=False, format=format, numberify=numberify, show_errors=show_errors)
    buffer = io.StringIO()
    if output is not None:
        output = output.resolve()
        if shell.source_file is not None:
            _refuse_alias(output, shell.source_file, shell.context)
    _replay_init(shell, buffer if output is not None else None)
    from beanquery import Error as BeanqueryError

    try:
        shell.onecmd(query_string)
    except BeanqueryError as exc:
        # `bean-query` let these escape as a Python traceback; name the problem instead.
        raise _usage_error(exc, query_string, shell.context, []) from None
    except (ValueError, OverflowError) as exc:
        evaluation = _evaluation_error(exc, query_string, [])
        if evaluation is None:
            raise
        raise evaluation from None
    if output is not None:
        _export(shell, output, buffer.getvalue())


def _run_stored(shell: Any, arg: str) -> None:
    """`.run`: list stored queries, run one or all; a missing name is a usage error.

    Upstream prints `error: query "x" not found` and returns, which a one-shot
    then reports as success.
    """
    import shlex

    cleaned = arg.rstrip("; \t")
    if not cleaned:
        if shell.queries:
            print("\n".join(name for name in sorted(shell.queries)), file=shell.outfile)
        return
    if cleaned == "*":
        for name, query in sorted(shell.queries.items()):
            if _stored_body_is_empty(query.query_string):
                # One placeholder must not stop every other stored query answering.
                protocol.note(f'Skipped stored query "{name}": its body is empty.')
                continue
            print(f"{name}:", file=shell.outfile)
            shell.execute(query.query_string, default_close_date=query.date)
            print(file=shell.outfile)
            print(file=shell.outfile)
        return
    known = ", ".join(sorted(shell.queries)) or "(none)"
    # A name works exactly as `.run` lists it: `this month's food` is one
    # stored query, not an unterminated shell quote (w5/237).
    name = cleaned
    query = shell.queries.get(name)
    if query is None:
        try:
            parts = shlex.split(cleaned)
        except ValueError as exc:
            raise protocol.UsageError(
                f'cannot read the "run" query name: {exc}.',
                details=[
                    'Wrap a name containing a quote character in the other kind, e.g. .run "it\'s mine".',
                    f"Stored queries in this ledger: {known}.",
                ],
            ) from None
        if len(parts) != 1:
            raise protocol.UsageError('too many arguments for "run" command')
        name = parts[0]
        query = shell.queries.get(name)
    if query is None:
        raise protocol.UsageError(
            f'query "{name}" not found.',
            details=[f"Stored queries in this ledger: {known}."],
        )
    if _stored_body_is_empty(query.query_string):
        raise protocol.UsageError(
            f'stored query "{name}" has an empty body.',
            details=["Write its BQL between the second pair of quotes of the query directive."],
        )
    shell.execute(query.query_string, default_close_date=query.date)


def _stored_body_is_empty(body: str) -> bool:
    """Whether a stored `query` directive holds no BQL: blank, or only comments.

    The parser raises a bare `IndexError` on `""` and a caret under nothing on
    whitespace, neither of which says which directive to fix (w5/276).
    """
    return not _code_mask(body, literals=False).strip("; \t\r\n")


def _split_dot_arguments(command: str, arg: str) -> list[str]:
    """Split a dot command's arguments, naming an unbalanced quote as a usage error.

    Upstream calls `shlex.split` bare, so `.describe 'x` escaped as a Python
    traceback under `--source` and as `ValueError: No closing quotation` on
    `--file` (w5/293). `.run` already words this (w5/237).
    """
    import shlex

    try:
        return shlex.split(arg)
    except ValueError as exc:
        raise protocol.UsageError(
            f'cannot read the "{command}" arguments: {exc}.',
            details=["Close the quote, or wrap a value containing a quote character in the other kind."],
        ) from None


def _shell_error(shell: Any, message: str, report: Callable[[str], None]) -> None:
    """A shell command's own complaint; in a one-shot it is a usage error (w5/236).

    Upstream prints `error: …` and returns — an unknown command, a bad
    `.set` or `.format` — which is right at the prompt and while the init file
    replays. A one-shot then reported success: exit 0, an empty JSON success
    envelope, and an `--output` export replaced with nothing.
    """
    if shell.interactive or shell.replaying_init:
        report(message)
        return
    raise protocol.UsageError(
        f"Cannot run this shell command: {message}.",
        details=["Run bea query .help to list the shell commands."],
    )


def _help_to_outfile(shell: Any, show: Callable[[str], None], arg: str) -> None:
    """Run upstream's `.help` with its stream pointed at the shell's outfile.

    Upstream `cmd.Cmd.do_help` writes to `self.stdout`, which starts as process
    stdout. That put a second document on the engine's stdout beside the JSON
    envelope, and under `--output` printed the help to the terminal while the
    empty buffer replaced the export (w5/289).
    """
    previous = shell.stdout
    shell.stdout = shell.outfile
    try:
        show(arg)
    finally:
        shell.stdout = previous


def _recovering(shell: Any, dispatch: Callable[[str], Any], line: str) -> Any:
    """Dispatch one shell line; an interactive mistake is reported, not raised.

    A mistake typed at the prompt is ordinary input, not a crash. Upstream's
    `cmdloop` catches everything and renders anything it does not recognize
    with `traceback.format_exc()`, so `.run` naming no stored query printed a
    Python stack — and threw away the `details` line listing the queries that
    do exist, which the one-shot form shows. `--debug` is the documented way
    to ask for a traceback.

    One-shot execution must still propagate: its exit code and its JSON error
    envelope are built from this exception.

    Upstream renders its own errors well only when they carry a parse
    position. One without — `ORDER BY 3` over two columns — got the same
    traceback, so it is said here in the one-shot's words (w5/109).
    """
    from beanquery import Error as BeanqueryError

    try:
        return dispatch(line)
    except protocol.EngineError as exc:
        if not shell.interactive:
            raise
        protocol.note(str(exc))
        for detail in exc.details or ():
            protocol.note(detail)
        # The translation raised `from None`; the mistake's own stack is the context.
        _debug_traceback(shell, exc.__context__ or exc)
        return False
    except BeanqueryError as exc:
        if not shell.interactive or getattr(exc, "parseinfo", None):
            raise
        protocol.note(f"Cannot run this BQL query: {exc}.")
        _debug_traceback(shell, exc)
        return False
    except OSError:
        raise
    except Exception as exc:
        # Upstream's loop would print this with its traceback and carry on.
        if not shell.interactive:
            raise
        protocol.note(f"error: {unexpected_failure(exc)}")
        _debug_traceback(shell, exc)
        return False


def unexpected_failure(exc: Exception) -> str:
    """One line for an exception upstream's shell raised and bea has no wording for.

    `query --source` hands the query to upstream, whose display context gives
    an amount twelve integer digits at most: a 10^12 VND balance raised
    `InvalidOperation` there and printed a 200-line traceback, where `--file`
    answers (w5/472).
    """
    from decimal import DecimalException

    if isinstance(exc, DecimalException):
        return (
            f"Decimal arithmetic failed while running or printing this query ({type(exc).__name__}). Upstream's "
            "rendering holds an amount to twelve integer digits; query the ledger with --file to print larger ones."
        )
    return f"{type(exc).__name__}: {exc}".rstrip(".") + "."


def _debug_traceback(shell: Any, exc: BaseException) -> None:
    """Under `bea --debug`, follow a prompt explanation with the stack behind it."""
    import traceback

    if shell.debug:
        protocol.note("".join(traceback.format_exception(exc)).rstrip())


def _export(shell: Any, output: Path, text: str) -> None:
    """Write a one-shot's `--output` export, unless a shell command printed nothing.

    `.history`, `.reload`, `.run` over a ledger with no stored queries, and
    `.errors` over one that has errors (upstream prints those to the terminal)
    leave the buffer empty, and writing it replaced the last good export with a
    zero-byte file under exit 0 (w5/289). A query that renders nothing is still
    an answer and is written.
    """
    if not text and not shell.ran_query:
        protocol.note(f"Nothing was written to {output}: this shell command printed no result to export.")
        return
    _write_export(output, text)


def _write_export(output: Path, text: str) -> None:
    """Replace `output` with `text` atomically, keeping an existing file's mode.

    Opening the destination itself truncated it before the bytes were safely
    down, so a write that failed partway — a full disk, a size limit — left a
    fragment of the new result where the last good export had been.
    `candidate_file` is the engine's own sibling-temp primitive: same
    directory, so the replace is atomic, with fsync and cleanup already
    handled. The frontend has its own `cli.utils.atomic_write` for the JSON
    path.
    """
    from bea_engine.ledger.write import candidate_file

    try:
        status = output.stat()
    except FileNotFoundError:
        mode = None
    else:
        if not stat.S_ISREG(status.st_mode):
            # A device or FIFO (`-o /dev/null`): there is no sibling to stage
            # in, and replacing it would swap the device for a regular file.
            with output.open("w", encoding="utf-8") as stream:
                stream.write(text)
            return
        mode = stat.S_IMODE(status.st_mode)
        if not os.access(output, os.W_OK):
            # The rename would succeed in a writable directory; a read-only
            # export is refused the way the frontend's JSON writer refuses it.
            raise protocol.AuthError(f"Output file {output} is read-only and cannot be replaced. Nothing was written.")
    with candidate_file(output, text, mode=0o666 if mode is None else 0o600) as candidate:
        if mode is not None:
            candidate.chmod(mode)
        os.replace(candidate, output)


def _gate(errors: list[str], allow_errors: bool, file: Path | None = None) -> list[str]:
    """Refuse to answer from a ledger that does not load, unless told otherwise.

    A total computed from a ledger with errors reads as authoritative and is
    not, so the refusal happens here — before the query runs — and the caller
    opts into a partial answer. `bea` decides which it wants from whether
    stdout is a terminal and whether `--allow-errors` was passed.
    """
    if errors and not allow_errors:
        from bea_engine.ledger.write import root_read_hint

        hint = root_read_hint(file) if file is not None else None
        raise protocol.LedgerError(
            f"Ledger has {len(errors)} error(s). Pass --allow-errors to report anyway.",
            details=[*errors, *([hint] if hint else [])],
        )
    return errors


def interactive(
    file: Path,
    *,
    format: str = "text",
    output: Path | None = None,
    numberify: bool = False,
    show_errors: bool = True,
    allow_errors: bool = False,
    spreadsheet_safe: bool = False,
    debug: bool = False,
) -> None:
    """Upstream's interactive shell, on this process's terminal.

    `bea` runs this command with the streams inherited, so stdin really is the
    customer's terminal: readline, the pager and Ctrl-C behave as they do under
    `bean-query` itself.

    A strict read refuses the session before the prompt appears, the same way
    it refuses a one-shot query: every answer this session gives would come
    from the same partially-loaded ledger. `--strict` used to be dropped here,
    so the shell answered leniently — and `--no-errors`, which is only meant to
    quieten the startup banner, then hid the one remaining sign that the ledger
    was invalid.
    """
    import warnings

    warnings.filterwarnings("always")
    shell = build_shell(file, sys.stdout, interactive=True, format=format, numberify=numberify, show_errors=show_errors)
    shell.spreadsheet_safe = spreadsheet_safe
    shell.debug = debug
    # After build_shell, which is what loads the ledger, and before cmdloop.
    _gate([format_error(error, ledger_file=file) for error in shell.context.errors], allow_errors, file)
    # The policy outlives startup: `.reload` swaps in whatever the file holds
    # now, and every later query re-checks it (see PreciseShell.execute).
    shell.allow_errors = allow_errors
    destination = None
    if output is not None:
        _refuse_alias(output, file, shell.context)
        destination = output.open("w")
    try:
        _replay_init(shell, destination)
        shell.cmdloop()
    finally:
        if destination is not None:
            destination.close()


def build_shell(
    file: Path,
    stream: TextIO,
    *,
    interactive: bool = False,
    format: str = "text",
    numberify: bool = False,
    show_errors: bool = True,
) -> Any:
    """Upstream's `BQLShell`, attached to the exact file and rendering at result precision."""
    from beanquery.cursor import Column
    from beanquery.numberify import numberify_results
    from beanquery.shell import FORMATS, BQLShell
    from beanquery.sources.beancount import Metadata

    class PreciseShell(BQLShell):  # type: ignore[misc]  # beanquery does not ship type annotations
        outfile: TextIO
        # The read policy for queries after a `.reload`. One-shot callers gate
        # the load themselves before executing, so only `interactive()` turns
        # this off, once the startup load has passed its own gate.
        allow_errors: bool = True
        # `--spreadsheet-safe`: neutralise formula-looking text in CSV cells.
        spreadsheet_safe: bool = False
        # Why the last `.reload` could not read the ledger, until one can.
        reload_failure: str | None = None
        # `bea --debug`: a mistake at the prompt also prints its traceback.
        debug: bool = False
        # The init file is being replayed: its mistakes stay upstream's notes.
        replaying_init: bool = False
        # BQL reached `execute`: an empty rendering is then a result, not silence.
        ran_query: bool = False

        def error(self, message: str) -> None:
            _shell_error(self, message, super().error)

        def do_output(self, arg: str) -> None:
            """Send output to FILE or restore the original output stream."""
            # Beanquery 0.2.0 calls open(sys.stdout) on reset and closes the old
            # stream before opening its replacement. Remove this override when
            # upstream supports reset and failed redirection without losing output.
            _redirect_output(self, arg, stream, file)

        def do_reload(self, arg: Any = None) -> None:
            """Reload the Beancount input file."""
            # Upstream attaches by DSN and therefore inherits its urlparse()
            # path mangling; attach the freshly loaded entries instead.
            # Load first, swap on success. Clearing the errors before a load
            # that then raised — the file unreadable or gone — left the old
            # entries beside an empty error list: the strict gate passed and
            # the session answered from the earlier load (w5/106).
            try:
                # A Ctrl-C mid-parse is raised here, after the load: the
                # startup load ends the session and this one is not swapped in.
                with stopping.deferring_interrupt():
                    loaded = load(file)
            except Exception as exc:
                if "entries" not in self.context.tables:
                    # The constructor's first load: there is no session to
                    # keep open, and its failure keeps its own exit status.
                    raise
                reason = str(exc)
                if isinstance(exc, OSError) and exc.strerror:
                    # Name an include that failed; the root is already named.
                    inner = "" if str(exc.filename or file) == str(file) else f": {exc.filename}"
                    reason = exc.strerror + inner
                reason = (reason.strip().splitlines() or [type(exc).__name__])[0]
                self.reload_failure = f"Cannot reload {file}: {reason}; queries are refused until a .reload succeeds."
                raise protocol.LedgerError(self.reload_failure) from None
            self.reload_failure = None
            self.context.errors.clear()
            self.context.options.clear()
            self.context.attach(LEDGER_DSN, **loaded)
            self._extract_queries(self.context.tables["entries"].entries)
            if self.context.errors and self.show_load_errors:
                _print_load_errors(self.context.errors, sys.stderr)
            if self.context.errors and not self.allow_errors:
                # Said even under `--no-errors`: that flag quietens the banner,
                # it does not waive the strict read the session opened with.
                protocol.note(
                    f"Ledger has {len(self.context.errors)} error(s); queries are refused until "
                    "it loads cleanly. Fix the ledger and .reload, or reopen with --allow-errors."
                )

        def do_errors(self, arg: Any = None) -> None:
            """Print the errors that occurred during Beancount input file parsing."""
            if self.reload_failure:
                print(self.reload_failure, file=self.outfile)
            elif self.context.errors:
                _print_load_errors(self.context.errors, sys.stdout)
            else:
                super().do_errors(arg)

        def do_help(self, arg: str) -> None:
            """List commands, writing to outfile so one-shot JSON stays clean."""
            _help_to_outfile(self, super().do_help, arg)

        def do_parse(self, arg: str) -> None:
            """Print the parsed sexp to outfile (not process stdout)."""
            print(self.parse(arg).tosexp(), file=self.outfile)

        def do_run(self, arg: str) -> None:
            """Run a named stored query, or list them; missing names are usage errors."""
            _run_stored(self, arg)

        def do_describe(self, arg: str) -> None:
            """Describe table or structured type."""
            _split_dot_arguments("describe", arg)
            super().do_describe(arg)

        def do_set(self, arg: str) -> None:
            """Set shell settings variables."""
            _split_dot_arguments("set", arg)
            super().do_set(arg)

        def execute(self, query: Any, **kwargs: Any) -> Any:
            """Prepare BQL here, where every entry path actually arrives.

            `_executed` wraps the *outer* request, which for `.run accounts` is
            the dot command rather than the stored SQL — so a stored or
            interactively typed query skipped both reserved-table quoting and
            the empty-window refusal. The same text then answered differently
            depending on how it was submitted: `FROM accounts` counted three
            accounts directly and four postings through `.run`, and a zero-day
            window returned `(no rows)` instead of saying it spans no days.

            Upstream funnels every statement through here — dot commands go to
            `do_*` instead — so this is the one place that sees BQL and only
            BQL. Preparation is idempotent (the quoting pattern skips names
            already quoted), which is what lets the outer wrapper stay as it is
            for the JSON path, which never builds a shell.

            It is also where a strict session re-applies its read policy: the
            startup gate saw only the first load, and `.reload` used to swap
            in an invalid ledger that typed and stored queries then answered
            from as if nothing had changed.
            """
            self.ran_query = True
            if self.reload_failure:
                # Lenient sessions too: what is attached is the load before
                # the failed one, not a partial answer to opt into.
                raise protocol.LedgerError(self.reload_failure)
            if not self.allow_errors:
                _gate([format_error(error, ledger_file=file) for error in self.context.errors], False, file)
            statement = ""
            if isinstance(query, str):
                _refuse_statement_tail(query)
                query = statement = _quote_reserved_tables(unicodedata.normalize("NFC", query))
                _refuse_empty_window(query, [], file=file)
            return _compiled(
                partial(super().execute, query, **kwargs),
                statement,
                lambda: [format_error(error, ledger_file=file) for error in self.context.errors],
                None if self.interactive else self.context,
            )

        def onecmd(self, line: str) -> Any:
            return _recovering(self, self._dispatch, line)

        def _dispatch(self, line: str) -> Any:
            # Ledger text loads NFC-normalized, so interactive input is too; a
            # pasted NFD literal would otherwise miss the identical NFC row.
            line = unicodedata.normalize("NFC", line)
            # A query that opens with a comment (`/* … */`, `;`) has no leading
            # identifier, so `cmd.Cmd.parseline` finds no command and upstream
            # returns without running it: empty output, exit 0. Hand any such
            # non-blank line to the parser, which runs it or reports why not.
            command_name, _, parsed = self.parseline(line)
            if parsed and not command_name:
                return self.execute(parsed)
            # Keep familiar shell commands as quiet aliases for beanquery's
            # dot commands. SQL and genuine query warnings are unchanged.
            stripped = line.lstrip()
            command = stripped.split(maxsplit=1)[0].lower() if stripped else ""
            if command in {"clear", "errors", "exit", "help", "history", "parse", "quit", "run", "set"}:
                line = "." + command + stripped[len(command) :]
            return super().onecmd(line)

        _printing = False

        def on_Select(self, statement: Any) -> Any:  # noqa: N802 - beanquery dispatch name
            cursor = self.context.execute(statement)
            description, rows = cursor.description, cursor.fetchall()
            # A `PRINT` returns entries by construction. With no rows its lone
            # column is typed `object`, which the guard below read as a column
            # `SELECT`: an empty year was refused, with the advice to "use
            # PRINT" (w5/102).
            if self.settings.format == "beancount" and not self._printing:
                _require_entries(description, rows)
            if not rows:
                protocol.note("(no rows)")
            dcontext = result_context(rows)
            if self.settings.numberify:
                description, rows = numberify_results(description, rows, dcontext.build())
            with self.output as out:
                if self.settings.format == "csv":
                    # Upstream CSV reuses text DecimalRenderer padding. Emit
                    # unpadded machine cells so spreadsheets and Decimal() parse.
                    return _render_csv(description, rows, out, spreadsheet_safe=self.spreadsheet_safe)
                if self.settings.format == "beancount":
                    return _render_beancount(rows, out, file)
                if self.settings.format == "text":
                    rows = [tuple(_inert_cell(_text_cell(value)) for value in row) for row in rows]
                    # Upstream renders `set` sorted and separated but has no
                    # renderer for `frozenset[str]`, the type of `tags` and
                    # `links` on `#notes` and `#documents`: those cells printed
                    # the Python repr in hash order (w5/179).
                    description = [
                        Column(column.name, set)
                        if (get_origin(column.datatype) or column.datatype) is frozenset
                        else column
                        for column in description
                    ]
                    # A metadata cell is already its text (`_metadata_cell`);
                    # upstream's renderers for these columns expect the dict.
                    description = [
                        Column(column.name, str) if column.datatype in (dict, Metadata) else column
                        for column in description
                    ]
                renderer = FORMATS[self.settings.format]
                if self.settings.format == "text":
                    with _fixed_point_text():
                        return renderer(description, rows, out, dcontext=dcontext, **self.settings.todict())
                return renderer(description, rows, out, dcontext=dcontext, **self.settings.todict())

        def on_Print(self, statement: Any) -> Any:  # noqa: N802 - beanquery dispatch name
            # Upstream PRINT forces the beancount renderer, silently ignoring
            # `--format csv`. Refuse that combination so agents do not get
            # directive text labeled as CSV.
            if self.settings.format == "csv":
                raise protocol.UsageError(
                    "PRINT renders Beancount directives; --format csv cannot represent them. "
                    "Use --format text or --format beancount, or SELECT for a CSV table."
                )
            self._printing = True
            try:
                return super().on_Print(statement)
            finally:
                self._printing = False

    # Upstream builds each statement's help topic from the docstring of the
    # handler defined on this class; an override without one crashes `help
    # select` and `help print` formatting a missing docstring.
    for name, handler in vars(PreciseShell).items():
        if name.startswith("on_") and handler.__doc__ is None:
            handler.__doc__ = getattr(BQLShell, name).__doc__
    # `runinit=False`: upstream would replay the init file inside the
    # constructor, before `self.context` exists, so a guarded `.output` there
    # failed every query. Callers replay it once the ledger is loaded.
    make = partial(PreciseShell, LEDGER_DSN, stream, interactive, False, format, numberify, show_errors)
    shell = _with_line_editor(make) if interactive else make()
    # Both one-shot and interactive tables keep full headers by default.
    # Upstream narrow=True treats the boolean as width 1 and cuts count(*)
    # to c/co. Interactive users can still explicitly `.set narrow true`.
    shell.settings.narrow = False
    return shell


def _print_load_errors(errors: Any, out: TextIO) -> None:
    """Upstream's load-error block, with control characters as visible `\\xNN`.

    `printer.print_errors` renders each offending entry verbatim, and the shell
    owns the terminal, so the frontend's inert-text filter never sees it: a
    payee carrying `\\x1b[2J` erased the "does not balance" line printed just
    above it — the only sign in a lenient session that answers are partial.
    Line feeds keep the block's shape; a carriage return would redraw over the
    line it sits on, so it is escaped with the rest.
    """
    from beancount.parser import printer

    from bea_engine.ledger.text import CONTROL_CHARACTERS, visible_escape

    for error in errors:
        block = printer.format_error(error) + "\n"  # type: ignore[no-untyped-call]
        out.write(CONTROL_CHARACTERS.sub(visible_escape, block.replace("\r", "\\x0d")))


_BARE_CARRIAGE_RETURN = re.compile(r"\r(?!\n)")


def _inert_cell(value: Any) -> Any:
    """A text-table cell whose control characters print as visible `\\xNN`.

    Ledger strings are untrusted: a narration carrying `\\x1b[2J` cleared the
    reader's terminal, because the table goes straight to a TTY (Click only
    strips such sequences on a pipe). Line breaks stay, so a multi-line value
    keeps its shape; JSON, CSV and `beancount` output keep the exact value.

    A carriage return is a line break only as part of CRLF. On its own it is
    cursor movement: the rest of the cell was drawn over the row's first
    columns, so a narration could replace the date and payee beside it (w5/108).
    """
    from bea_engine.ledger.text import CONTROL_CHARACTERS, visible_escape

    if isinstance(value, str):
        value = _BARE_CARRIAGE_RETURN.sub(r"\\x0d", value)
        return CONTROL_CHARACTERS.sub(visible_escape, value)
    if isinstance(value, frozenset | set):
        return type(value)(_inert_cell(item) for item in value)
    if isinstance(value, tuple) and not hasattr(value, "_fields"):
        return tuple(_inert_cell(item) for item in value)
    return value


def _require_entries(description: Any, rows: Any) -> None:
    """Refuse a column result under the beancount format before rendering it.

    Upstream's renderer unpacks every row as a single directive, so a column
    `SELECT` fails inside it with 'too many values to unpack' or a missing
    `meta` attribute. `PRINT` answers one directive per row; the ledger is fine
    either way, so this is a usage failure rather than a validation one.

    An empty result keys on the cursor, not the rows: `SELECT entry` types its
    lone column as the directive, while a column `SELECT` types it scalar, so
    emptiness can no longer hide an incompatible format behind "(no rows)".
    """
    from beancount.core.data import ALL_DIRECTIVES

    columns = tuple(description or ())
    entries_column = len(columns) == 1 and (
        columns[0].datatype in ALL_DIRECTIVES
        or (rows and all(len(row) == 1 and isinstance(row[0], ALL_DIRECTIVES) for row in rows))
    )
    if entries_column:
        return
    raise protocol.UsageError(
        "--format beancount prints directives, so the query must return entries; "
        "use PRINT, or --format text or csv for a column result."
    )


def _source_location(entry: Any) -> tuple[Any, Any]:
    meta = getattr(entry, "meta", None) or {}
    return (meta.get("filename"), meta.get("lineno"))


def _render_beancount(rows: Any, out: TextIO, file: Path) -> None:
    """Use the writer's syntax fixes with upstream's grouping and exact precision."""
    from beancount.core.data import Commodity, Document, Pad, Transaction
    from beancount.core.display_context import DisplayContext

    from bea_engine.ledger.writer import DirectivePrinter

    # Like upstream's Beancount renderer, a fresh display context retains each
    # number's natural precision instead of rounding to a result-column width.
    printer = DirectivePrinter(DisplayContext())  # type: ignore[no-untyped-call]
    # Beancount synthesizes a `P` transaction at each used pad's own location.
    # Printed beside the pad that produced it, the reloaded export books the
    # padding twice over and reports that pad unused, so the export of a valid
    # ledger failed `check` (w5/085). The pad derives it again on reload; a
    # padding transaction selected without its pad is still printed.
    pads = {_source_location(entry) for (entry,) in rows if isinstance(entry, Pad)}
    rows = [
        (entry,)
        for (entry,) in rows
        if not (isinstance(entry, Transaction) and entry.flag == "P" and _source_location(entry) in pads)
    ]
    previous_type = type(rows[0][0]) if rows else None
    for (entry,) in rows:
        entry_type = type(entry)
        if entry_type in (Transaction, Commodity) or entry_type is not previous_type:
            out.write("\n")
            previous_type = entry_type
        if isinstance(entry, Document):
            entry = entry._replace(filename=_portable_document_path(str(entry.filename), file))
        out.write(printer(entry))


def _portable_document_path(filename: str, file: Path) -> str:
    """A document path as an export beside the root ledger has to spell it.

    The loader makes every document path absolute. Printed that way, the export
    names the machine it ran on, and `check` reports it once the file is saved
    anywhere but beside the ledger (w5/229). A path inside the root ledger's
    directory prints relative to that directory: the export is one flat file,
    so a path an included file wrote relative to itself is respelled from the
    root. The name is the one written, so a symlinked attachment keeps it; a
    path outside the directory stays absolute.
    """
    root = os.path.dirname(os.path.abspath(file))
    try:
        resolved, base = Path(filename).resolve(), Path(root).resolve()
        if not os.path.isabs(filename) or not resolved.is_relative_to(base):
            return filename
        named = os.path.relpath(filename, root)
        # The loader may name the file through a different link than `--file`.
        return str(resolved.relative_to(base)) if named.startswith(os.pardir) else named
    except (OSError, ValueError):
        return filename


def _render_csv(description: Any, rows: Any, out: TextIO, *, spreadsheet_safe: bool = False) -> None:
    """Write CSV without text-table decimal alignment padding."""
    import csv

    writer = csv.writer(out)
    writer.writerow([column.name for column in description or ()])
    for row in rows:
        cells = [_csv_cell(value) for value in row]
        if spreadsheet_safe:
            pairs = zip(row, cells, strict=True)
            cells = [_inert_formula(cell) if isinstance(value, str) else cell for value, cell in pairs]
        writer.writerow(cells)


#: What a spreadsheet reads as the start of a formula (OWASP's CSV-injection list).
_FORMULA_TRIGGERS = ("=", "+", "-", "@", "\t", "\r")


def _inert_formula(cell: str) -> str:
    """A text cell a spreadsheet shows as text: a leading `'` when it would start a formula.

    Only for string values, under `--spreadsheet-safe`: payees and narrations
    often come from imported bank exports, but numbers and amounts keep their
    sign, and the default CSV keeps every value exactly as the ledger has it.
    """
    return "'" + cell if cell.startswith(_FORMULA_TRIGGERS) else cell


def _csv_cell(value: Any) -> str:
    """One unpadded CSV field from a BQL cell.

    Metadata is the text table's cell, user keys only. A directive is the
    Beancount text `--format beancount` prints for it. Both used to go through
    the JSON walk and `str()`, which leaked the loader's `filename`, `lineno`
    and `__tolerances__` keys — an absolute path in every exported row.
    """
    from beancount.core.data import ALL_DIRECTIVES

    if value is None:
        return ""
    if type(value) is dict:
        return _metadata_cell(value)
    if isinstance(value, ALL_DIRECTIVES):
        from beancount.core.display_context import DisplayContext

        from bea_engine.ledger.writer import DirectivePrinter

        return DirectivePrinter(DisplayContext())(value).strip("\n")  # type: ignore[no-untyped-call]
    rendered = protocol._jsonable(value)
    return _csv_from_jsonable(rendered)


def _is_metadata(value: Any) -> bool:
    """True for a directive's or posting's metadata, which the loader stamps with its location."""
    return isinstance(value, dict) and "filename" in value and "lineno" in value


def _user_metadata(meta: Mapping[str, Any]) -> dict[str, Any]:
    """The keys a ledger author wrote: upstream's `MetadataRenderer` filter."""
    return {key: item for key, item in meta.items() if key not in {"filename", "lineno"} and not key.startswith("__")}


def _metadata_cell(meta: Mapping[str, Any]) -> str:
    """A metadata dictionary as one text or CSV cell: the JSON output's object.

    `str()` of the dict was a Python repr — `Decimal('1E-8')`,
    `datetime.date(2026, 1, 7)`, `True` — which no consumer can parse and which
    spelled a tiny number with the exponent the rest of the output never uses
    (w5/230). The JSON walk gives fixed-point numbers, ISO dates and amounts as
    `number`/`currency` objects, exactly as `--json` returns the same cell.
    """
    return json.dumps(protocol._jsonable(_user_metadata(meta)), ensure_ascii=False)


def _text_cell(value: Any) -> Any:
    """A text-table cell: metadata as its JSON text, a directive as its Beancount text.

    Anything else loses only the loader's internal keys. A directive cell was
    its Python repr, `Decimal('1E-8')` and `datetime.date(...)` included,
    while the CSV cell beside it was already Beancount text (w5/294).
    """
    from beancount.core.data import ALL_DIRECTIVES

    if isinstance(value, ALL_DIRECTIVES):
        return _csv_cell(value)
    return _metadata_cell(value) if type(value) is dict else _public_value(value)


@contextmanager
def _fixed_point_text() -> Iterator[None]:
    """Render the `--file` text table with fixed-point numbers and multi-line cells.

    Upstream's `DecimalRenderer` pads with an f-string and `ObjectRenderer` is
    `str()`, so `0.00000001` printed as `1E-8` in a number column, a `-m`
    column and an `entry_meta()` cell, while the position beside it, the CSV
    and the JSON all said `0.00000001` (w5/294). The swap lasts one render, so
    native `--source` keeps upstream's table.
    """
    from beanquery import query_render

    swapped = _text_renderers()
    saved = {dtype: query_render.RENDERERS[dtype] for dtype in swapped}
    query_render.RENDERERS.update(swapped)
    try:
        yield
    finally:
        query_render.RENDERERS.update(saved)


def _whole(value: Decimal) -> Decimal:
    """A positive-exponent decimal as the same number with its zeros written out.

    `Decimal("1.5E+3")` becomes `Decimal("1500")`: parsed from its fixed-point
    text, never rounded to the context's precision.
    """
    exponent = value.as_tuple().exponent
    return Decimal(format(value, "f")) if isinstance(exponent, int) and exponent > 0 else value


@cache
def _text_renderers() -> dict[type, type]:
    from beanquery import query_render

    registered = dict(query_render.RENDERERS)

    class FixedPointDecimalRenderer(query_render.DecimalRenderer):  # type: ignore[misc]
        """Upstream's decimal-point alignment, never in scientific notation.

        Upstream measures and prints a positive exponent (`round(x, -2)`) as
        `1.5E+3`, and compares a NaN's or an infinity's exponent, a letter,
        with `>`, a TypeError that ended the query (w5/471). Such a value is
        measured and printed as its fixed-point digits, and a non-finite one
        as its name, as CSV and JSON print them.
        """

        nintegral: int

        def update(self, value: Decimal) -> None:
            if not value.is_finite():
                self.nintegral = max(self.nintegral, len(str(value)))
                return
            super().update(_whole(value))

        def format(self, value: Decimal) -> str:
            if not value.is_finite():
                return str(value).rjust(self.nintegral).ljust(self.maxwidth)
            value = _whole(value)
            # Upstream's padding with a fixed-point spelling: the widths it
            # measured from `as_tuple()` already count the zeros.
            n = value.as_tuple()
            left = self.nintegral - (max(1, len(n.digits) + n.exponent) + n.sign)  # type: ignore[operator]
            return f"{'':>{left}}{value:<{self.maxwidth - left}f}"

    class PlainObjectRenderer(query_render.ObjectRenderer):  # type: ignore[misc]
        def update(self, value: Any) -> None:
            text = self.format(value)
            lines = text if isinstance(text, list) else [text]
            self.maxwidth: int = max(self.maxwidth, *map(len, lines))

        def format(self, value: Any) -> str | list[str]:
            if isinstance(value, Decimal):
                return format(value, "f")
            text = str(value)
            # A directive's Beancount text spans lines; upstream lays a list
            # out one line per table row.
            return text.split("\n") if "\n" in text else text

    # Subclassing registers each class in upstream's table for good; keep that
    # table as it was and swap these in only for one text render.
    query_render.RENDERERS.clear()
    query_render.RENDERERS.update(registered)
    return {Decimal: FixedPointDecimalRenderer, object: PlainObjectRenderer}


def _public_value(value: Any) -> Any:
    """A result cell without the loader's internal metadata, at any depth.

    Upstream hides `filename`, `lineno` and `__*` keys only for a column typed
    as entry metadata, so a posting's `meta`, or the metadata inside a whole
    directive, carried the ledger's absolute path into every rendering. Only
    text and JSON use this; `--format beancount` prints directives through the
    writer, which reads the internal keys and never writes them.
    """
    if _is_metadata(value):
        return _user_metadata(value)
    fields = getattr(value, "_fields", None)
    if fields is None or "meta" not in fields:
        return value
    changes: dict[str, Any] = {}
    if isinstance(value.meta, dict):
        changes["meta"] = _user_metadata(value.meta)
    if "postings" in fields and value.postings:
        changes["postings"] = [_public_value(posting) for posting in value.postings]
    return value._replace(**changes)


def _csv_from_jsonable(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, str | int):
        return str(value)
    if isinstance(value, dict):
        if "units" in value:
            units = _csv_from_jsonable(value["units"])
            cost = value.get("cost")
            if cost:
                return f"{units} {{{_csv_cost(cost)}}}"
            return units
        if "number" in value and "currency" in value:
            return f"{value['number']} {value['currency']}"
        return str(value)
    if isinstance(value, list):
        return ", ".join(_csv_from_jsonable(item) for item in value)
    return str(value)


def _csv_cost(cost: dict[str, Any]) -> str:
    """A lot's cost spec as Beancount writes it: number and currency, then date and label.

    Rendered as a bare amount, two lots at the same price became the same
    cell — `10 HOOL {100 USD}` twice — though the ledger, `--json` and every
    other machine-readable surface kept their dates and labels apart
    (w5/465).
    """
    parts = [_csv_from_jsonable(cost)]
    if cost.get("date"):
        parts.append(str(cost["date"]))
    if cost.get("label"):
        label = str(cost["label"]).replace("\\", "\\\\").replace('"', '\\"')
        parts.append(f'"{label}"')
    return ", ".join(parts)


def _executed(conn: Any, query_string: str, run: Any, ledger_errors: list[str], *, file: Path) -> Any:
    """Run a query, turning beanquery's terse complaint into one that names the problem."""
    from beanquery import Error as BeanqueryError

    # Ledger text loads NFC-normalized, so the query must be too: a regex or
    # comparison literal in another normalization would otherwise miss the
    # identical string. Keywords and column names are ASCII and pass through.
    statement = _quote_reserved_tables(unicodedata.normalize("NFC", query_string))
    if not statement.lstrip().startswith("."):
        # Dot commands are not BQL; a stored body `.run` reaches is checked
        # when the shell executes it.
        _refuse_statement_tail(statement, ledger_errors)
    _refuse_empty_window(statement, ledger_errors, file=file)
    try:
        return _compiled(lambda: run(statement), statement, lambda: ledger_errors)
    except BeanqueryError as exc:
        # Against the statement the parser saw: its offset counts the quotes
        # added around `accounts`/`balances`, not the text as typed (w5/178).
        raise _usage_error(exc, statement, conn, ledger_errors) from None


def _compiled(
    run: Callable[[], Any], statement: str, ledger_errors: Callable[[], list[str]], context: Any = None
) -> Any:
    """Run one BQL statement, naming the compile failures Beanquery lets escape raw.

    Every path that executes BQL — one-shot, `.run`, and a line typed at the
    prompt — comes through here, so they all explain the same failure the same
    way. The prompt used to print these as Python tracebacks while the one-shot
    named the column and what would work instead.

    With a `context`, Beanquery's own errors are explained here too, against
    the statement that actually ran: a stored query reached through `.run`
    used to be explained against the `.run NAME` text, so it lost the caret,
    the column suggestions and the set-column advice its direct form gets.
    The interactive prompt passes none and keeps upstream's rendering.
    """
    from beanquery import Error as BeanqueryError

    # Beanquery compiles a `~` pattern only while it evaluates a row, so a
    # malformed one failed as a ledger validation error (exit 1) — or not at
    # all, when the window held no rows. A constant pattern is checked here,
    # before anything runs, so both shapes are the same usage error (w5/103).
    from bea_engine.ledger.text import regex_reads_otherwise

    for pattern in _PATTERN_LITERAL.findall(statement):
        # First, so no compile warns: Python reads `[[:alpha:]]` as a set and
        # only warns, and the query then matches something else (w5/429).
        otherwise = regex_reads_otherwise(pattern[1:-1])
        if otherwise is not None:
            raise protocol.UsageError(
                f"Cannot run this BQL query: in the pattern {pattern[1:-1]!r}, {otherwise}.",
                details=[f"  {statement}"],
                ledger_errors=ledger_errors(),
            )
        try:
            re.compile(pattern[1:-1])
        except re.error as exc:
            raise _pattern_error(pattern[1:-1], exc, statement, ledger_errors()) from None
    try:
        return run()
    except re.error as exc:
        # A pattern that is not a constant — built by an expression — can only
        # fail here.
        raise _pattern_error(str(exc.pattern), exc, statement, ledger_errors()) from None
    except BeanqueryError as exc:
        if context is None:
            raise
        raise _usage_error(exc, statement, context, ledger_errors()) from None
    except OverflowError as exc:
        evaluation = _evaluation_error(exc, statement, ledger_errors())
        if evaluation is None:
            raise
        raise evaluation from None
    except ValueError as exc:
        # The parser converts literals as it reads them, so `2020-99-01`
        # surfaces as a bare ValueError from `date.fromisoformat` — a typo in
        # the query, not an engine failure (w1/085). Only an error raised
        # inside the parser, or one `_evaluation_error` recognizes as the
        # query's, is the query's; anything else propagates.
        literal = _parse_literal_error(exc)
        if literal is None:
            evaluation = _evaluation_error(exc, statement, ledger_errors())
            if evaluation is None:
                raise
            raise evaluation from None
        details = [f"  {statement}"]
        if literal == "date":
            details.append("Write dates as YYYY-MM-DD with a real month and day, for example 2020-02-29.")
        raise protocol.UsageError(
            f"Cannot run this BQL query: invalid {literal} literal: {exc}.",
            details=details,
            ledger_errors=ledger_errors(),
        ) from None
    except SyntaxError as exc:
        # Beanquery compiles a query to Python. `SELECT DISTINCT tags` makes it
        # emit code it cannot parse, and the SyntaxError that escapes says only
        # "cannot use starred expression here" — nothing about the query, or the
        # column, or what would work instead.
        columns = _set_columns(statement)
        if not columns:
            raise protocol.UsageError(
                f"Beanquery could not compile this BQL query: {exc}.",
                details=_SET_COLUMN_ADVICE,
                ledger_errors=ledger_errors(),
            ) from None
        named = ", ".join(columns)
        raise protocol.UsageError(
            f"BQL cannot use DISTINCT or GROUP BY on {named}: a set is not a value it can compare.",
            details=_SET_COLUMN_ADVICE,
            ledger_errors=ledger_errors(),
        ) from None
    except TypeError as exc:
        # The hashability check calls `issubclass(dtype, Hashable)`, which
        # raises TypeError on the parameterized `set[str]` behind `accounts` —
        # the GROUP BY equivalent of the non-hashable error tags and links get.
        # Anything else is a genuine bug and propagates untouched.
        grouped = [column for column in _grouped_columns(statement) if column in _SET_COLUMNS_PLUS_ACCOUNTS]
        if "issubclass" in str(exc) and grouped:
            named = ", ".join(grouped)
            raise protocol.UsageError(
                f"BQL cannot use DISTINCT or GROUP BY on {named}: a set is not a value it can compare.",
                details=_SET_COLUMN_ADVICE,
                ledger_errors=ledger_errors(),
            ) from None
        # A subquery joined by AND or OR is called as a row predicate, which
        # an EvalQuery node does not accept.
        if "EvalQuery" in str(exc):
            raise _scalar_subquery_error(ledger_errors()) from None
        # Beside an aggregate with no GROUP BY, every other column is grouped
        # by implicitly, and nothing checks it can be hashed until the first
        # row is aggregated (w5/260).
        ungroupable = _ungroupable_columns(exc)
        if ungroupable is not None:
            raise _implicit_group_error(ungroupable, ledger_errors()) from None
        raise
    except AttributeError as exc:
        # A scalar subquery in the SELECT list reaches scalar evaluation as an
        # EvalQuery node, which has no childnodes to evaluate.
        if "childnodes" in str(exc):
            raise protocol.UsageError(
                "BQL cannot use a subquery in the SELECT list.",
                details=["Filter with it instead: SELECT ... WHERE column IN (SELECT ...)"],
                ledger_errors=ledger_errors(),
            ) from None
        # Compared, negated or computed with, the same node is asked for the
        # dtype only a scalar expression has.
        if "EvalQuery" in str(exc):
            raise _scalar_subquery_error(ledger_errors()) from None
        raise


def _scalar_subquery_error(ledger_errors: list[str]) -> protocol.UsageError:
    return protocol.UsageError(
        "BQL cannot use a subquery as a single value.",
        details=["Filter with it instead: SELECT ... WHERE column IN (SELECT ...)"],
        ledger_errors=ledger_errors,
    )


def _ungroupable_columns(exc: TypeError) -> list[tuple[str, str]] | None:
    """The implicitly grouped `(column, type)` pairs Beanquery's aggregation could not hash.

    None unless the TypeError is that failure: an unhashable group key inside
    Beanquery's `execute_select`. The explicit `GROUP BY` form is refused when
    it compiles, with the column's name; here the name is read back from the
    frame that failed, since only the row's values say which column it was.
    """
    if "unhashable type" not in str(exc):
        return None
    tb = exc.__traceback__
    while tb is not None and tb.tb_next is not None:
        tb = tb.tb_next
    if tb is None:
        return None
    code = tb.tb_frame.f_code
    if code.co_name != "execute_select" or Path(code.co_filename).parent.name != "beanquery":
        return None
    scope = tb.tb_frame.f_locals
    query, key = scope.get("query"), scope.get("key") or ()
    targets = getattr(query, "c_targets", None) or []
    found: list[tuple[str, str]] = []
    for index, value in zip(getattr(query, "group_indexes", None) or [], key, strict=False):
        name = getattr(targets[index], "name", None) if index < len(targets) else None
        if isinstance(name, str) and not isinstance(value, Hashable) and (name, type(value).__name__) not in found:
            found.append((name, type(value).__name__))
    return found


def _implicit_group_error(columns: list[tuple[str, str]], ledger_errors: list[str]) -> protocol.UsageError:
    named = ", ".join(f"{name} ({kind})" for name, kind in columns) or "a selected column"
    details = ["A column selected beside an aggregate is grouped by, as if it were listed in GROUP BY."]
    for name, kind in columns:
        # `joinstr` reads a list and `str` most other values; no function can
        # read the parameterized set behind `accounts`, so it gets no recipe.
        if kind != "set":
            wrapped = f"joinstr({name})" if kind == "list" else f"str({name})"
            details.append(f"Group by its text instead: SELECT {wrapped}, ... GROUP BY {wrapped}")
    details.append("Or select it without the aggregate.")
    return protocol.UsageError(
        f"Cannot run this BQL query: BQL cannot group by {named}, which it cannot hash.",
        details=details,
        ledger_errors=ledger_errors,
    )


#: The string literal on the right of BQL's regex operators, quotes included.
_PATTERN_LITERAL = re.compile(r"""!?~\s*('[^']*'|"[^"]*")""")


def _evaluation_error(exc: Exception, statement: str, ledger_errors: list[str]) -> protocol.UsageError | None:
    """A value the query's own text asked for that Python refused, as a usage error, or None.

    `parse_date('x')`, date arithmetic past the calendar and a `LIMIT` beyond
    `sys.maxsize` are typos in the query, but they fail only while rows are
    evaluated — as dateutil's `ParserError`, an `OverflowError`, or islice's
    `ValueError` — so they reached the user as a ledger validation failure
    behind a Python class name (w5/314). Any other `ValueError` is not
    recognizably the query's and keeps propagating.
    """
    details = [f"  {statement}"]
    if isinstance(exc, OverflowError):
        if "date" in str(exc):
            details.append("Date arithmetic must stay between 0001-01-01 and 9999-12-31.")
        reason = str(exc)
    elif type(exc).__name__ == "ParserError" and type(exc).__module__.startswith("dateutil"):
        reason = f"cannot read a date: {exc}"
        details.append("parse_date reads text such as '2026-01-05'.")
    elif "islice()" in str(exc):
        reason = f"LIMIT must be at most {sys.maxsize}"
    else:
        return None
    return protocol.UsageError(f"Cannot run this BQL query: {reason}.", details=details, ledger_errors=ledger_errors)


def _pattern_error(pattern: str, exc: re.error, statement: str, ledger_errors: list[str]) -> protocol.UsageError:
    where = f" at position {exc.pos}" if exc.pos is not None else ""
    return protocol.UsageError(
        f"Cannot run this BQL query: {pattern!r} is not a valid regular expression: {exc.msg}{where}.",
        details=[f"  {statement}", "Escape a literal (, [, * or + with a backslash, for example '\\(partial'."],
        ledger_errors=ledger_errors,
    )


_SET_COLUMNS = ("tags", "links")

_SET_COLUMNS_PLUS_ACCOUNTS = ("tags", "links", "accounts")

_SET_COLUMN_ADVICE = [
    "`tags` and `links` hold a whole set per entry, so BQL cannot hash them.",
    "Distinct combinations: SELECT DISTINCT joinstr(tags) — one string per row; the order inside it is not stable.",
    "Counts per combination: SELECT joinstr(tags), count(*) GROUP BY joinstr(tags)",
    "One tag at a time: SELECT date, narration WHERE 'grocery' IN tags",
]


def _set_columns(query_string: str) -> list[str]:
    """The bare set-valued columns this query selects, which is what cannot be compared.

    Only a bare column is a problem — `joinstr(tags)` is a string and behaves
    like any other, which is why it is the recipe we point at.
    """
    try:
        from beanquery.parser import parse

        parsed = parse(query_string)
    except Exception:  # noqa: BLE001 - the query already failed; advice is best effort
        return []
    found: list[str] = []
    for target in getattr(parsed, "targets", None) or []:
        name = getattr(getattr(target, "expression", None), "name", None)
        if name in _SET_COLUMNS and name not in found:
            found.append(name)
    return found


def _grouped_columns(query_string: str) -> list[str]:
    """The columns this query groups by, for naming the set GROUP BY cannot hash."""
    try:
        from beanquery.parser import parse

        parsed = parse(query_string)
    except Exception:  # noqa: BLE001 - the query already failed; advice is best effort
        return []
    group_by = getattr(parsed, "group_by", None)
    # `GROUP BY 1` is an int and `GROUP BY root(account, 1)` a function node;
    # neither has a name, and reading one here replaced the real error with
    # this handler's own AttributeError (w5/177).
    targets = getattr(parsed, "targets", None) or []
    names = []
    for column in getattr(group_by, "columns", None) or []:
        # A position names its 1-based SELECT target: `GROUP BY 1` on
        # `accounts` still raised the raw `issubclass` TypeError (w5/313).
        if isinstance(column, int) and 0 < column <= len(targets):
            column = getattr(targets[column - 1], "expression", None)
        names.append(getattr(column, "name", None))
    return [name for name in names if isinstance(name, str)]


def _refuse_empty_window(query_string: str, ledger_errors: list[str], *, file: Path) -> None:
    """Refuse a `FROM OPEN ON … CLOSE ON …` window that can hold no entries.

    `CLOSE ON D` is exclusive, so `OPEN ON D CLOSE ON D` spans zero days while
    the `--from-date D --to-date D` filters everywhere else in `bea` span one.
    Answering `(no rows)` reads as "that day is empty" rather than "you asked
    for no days", so say which it is and how to ask for the day.
    """
    try:
        from beanquery.parser import ast, parse

        parsed = parse(query_string)
    except Exception:  # noqa: BLE001 - a dot command or a broken query; beanquery reports it
        return
    # Every dated window, not just the outer one: a subquery's `FROM OPEN ON D
    # CLOSE ON D` answered `(no rows)` just the same (w1/158).
    for clause in ast.walk(parsed):
        if isinstance(clause, ast.From):
            _refuse_window(clause.open, clause.close, ledger_errors, file=file)


def _refuse_window(begin: Any, end: Any, ledger_errors: list[str], *, file: Path) -> None:
    """Refuse one `OPEN ON begin CLOSE ON end` window that spans no days, or has no end date."""
    from datetime import date, timedelta

    from bea_engine.ledger.text import bea_command

    # A bare `CLOSE` is `True`, not a date, and closes at the end of the ledger.
    # Beside a dated `OPEN` Beanquery orders the two as dates and escapes with
    # a raw TypeError, which read as a ledger failure (exit 1) (w5/177).
    if isinstance(begin, date) and end is True:
        raise protocol.UsageError(
            f"BQL cannot run OPEN ON {begin} with a bare CLOSE: Beanquery needs the closing date here.",
            details=[
                "Add the date: CLOSE ON YYYY-MM-DD is exclusive, so name the day after the last one you want.",
                f"Or drop CLOSE: FROM OPEN ON {begin} alone already runs to the end of the ledger.",
            ],
            ledger_errors=ledger_errors,
        )
    if not isinstance(begin, date) or not isinstance(end, date) or begin < end:
        return
    if begin == end:
        message = (
            f"This BQL window covers no days: CLOSE ON {end} is exclusive, so it ends where OPEN ON {begin} starts."
        )
        details = [
            f"Use CLOSE ON {end + timedelta(days=1)} to cover {begin}.",
            f"Or run: {bea_command(file)} list transaction --from-date {begin} --to-date {begin}"
            " — those dates are inclusive.",
        ]
    else:
        message = f"This BQL window covers no days: OPEN ON {begin} starts after the exclusive CLOSE ON {end}."
        details = [f"Did you mean OPEN ON {end} CLOSE ON {begin + timedelta(days=1)}?"]
    raise protocol.UsageError(message, details=details, ledger_errors=ledger_errors)


def _parse_literal_error(exc: BaseException) -> str | None:
    """The literal kind (`date`, ...) a ValueError came from, if beanquery's parser raised it."""
    import traceback

    for frame in reversed(traceback.extract_tb(exc.__traceback__)):
        where = Path(frame.filename).parent
        if where.name == "parser" and where.parent.name == "beanquery":
            return frame.name if frame.name in {"date", "decimal", "integer"} else "literal"
    return None


def _usage_error(exc: Exception, query_string: str, conn: Any, ledger_errors: list[str]) -> protocol.UsageError:
    """Point at the offending token, and name the columns that do exist.

    Beanquery reports 'syntax error' with a byte offset and nothing else, which
    for a long query says only that one of its characters is wrong.
    """
    details = []
    position = getattr(getattr(exc, "parseinfo", None), "pos", None)
    if isinstance(position, int) and 0 <= position <= len(query_string):
        details.extend(_caret_lines(query_string, position))
    details.extend(_column_suggestions(str(exc), conn))
    if "non-hashable" in str(exc) and _set_columns(query_string):
        details.extend(_SET_COLUMN_ADVICE)
    # Not the interactive shell: under `--json` or without a terminal `bea query`
    # with no argument is itself a usage error, and `.tables` runs one-shot (w5/198).
    details.append("Run bea query .tables to list what you can query.")
    return protocol.UsageError(f"Cannot run this BQL query: {exc}.", details=details, ledger_errors=ledger_errors)


def _caret_lines(statement: str, position: int) -> list[str]:
    """The statement a line per detail, with a caret under the character at `position`.

    The parser's offset is absolute, so for a query spanning lines it has to
    become a column of the line it falls on; indented by the whole offset the
    caret sat alone, far to the right of every line shown. A tab is shown as
    one space so the caret's column is the token's.
    """
    lines = statement.splitlines(keepends=True) or [""]
    details = []
    start = 0
    for index, raw in enumerate(lines):
        text = raw.rstrip("\r\n").replace("\t", " ")
        details.append(f"  {text}")
        end = start + len(raw)
        if start <= position and (position < end or index == len(lines) - 1):
            details.append(f"  {' ' * min(position - start, len(text))}^")
        start = end
    return details


def _column_suggestions(message: str, conn: Any) -> list[str]:
    """Close matches for an unknown column, read from the table it was sought in."""
    match = re.search(r'column "([^"]+)" not found in table "([^"]+)"', message)
    if not match:
        return []
    unknown, table_name = match.groups()
    table = conn.tables.get(table_name)
    names = sorted(getattr(table, "columns", None) or ())
    if not names:
        return []
    close = difflib.get_close_matches(unknown, names, n=3, cutoff=0.6)
    if close:
        return [f"Did you mean {', '.join(close)}?"]
    return [f"Columns in {table_name}: {', '.join(names)}."]


def columns(description: Any) -> list[dict[str, str]]:
    """Name and declared type of each result column, so a caller can parse the rows."""
    if not description:
        return []
    return [{"name": column.name, "type": _type_name(column)} for column in description]


def _type_name(column: Any) -> str:
    datatype = getattr(column, "datatype", None)
    return getattr(datatype, "__name__", None) or str(datatype)


_PLUGIN_FAILURE = re.compile(r'^Error (importing|applying plugin) "([^"]+)":\s*(.*)$', re.DOTALL)
_TXN_LOCATION = re.compile(r"Transaction\(meta=\{'filename': '([^']*)', 'lineno': (\d+)")


def is_plugin_failure(error: Any) -> bool:
    """Whether a loader error is a plugin that could not be imported or raised while running."""
    message = getattr(error, "message", error)
    return isinstance(message, str) and _PLUGIN_FAILURE.match(message) is not None


def format_error(error: Any, ledger_file: Path | str | None = None) -> str:
    """One loader error as `file:line: message` — the frontend's detail line.

    Two loader messages arrive as internal Python artifacts and are rewritten
    here, the one boundary where error objects become display strings: plugin
    failures embed a full traceback with a `<load>:0` location, and duplicate
    reports embed two whole `Transaction(...)` reprs. Anything unrecognized
    keeps its legacy rendering rather than losing information.
    """
    source = getattr(error, "source", None) or {}
    message = getattr(error, "message", error)
    if isinstance(message, str):
        plugin = _plugin_message(message, ledger_file, source)
        if plugin is not None:
            return plugin
        duplicate = _duplicate_message(error, message)
        if duplicate is not None:
            return duplicate
        message = _booking_message(error, message)
    return f"{source.get('filename', '<ledger>')}:{source.get('lineno', 0)}: {message}"


_NO_LOT = re.compile(
    r"No position matches \"Posting\(account='(?P<account>[^']*)', units=(?P<units>[^,]+), .*\" "
    r"against balance (?P<held>.*)\Z",
    re.DOTALL,
)
_BALANCE_CURRENCY = re.compile(r"Invalid currency '(?P<currency>[^']*)' for Balance directive: ?\Z")
_NEGATIVE_COST = re.compile(
    r"Cost is negative: \"Cost\(number=Decimal\('(?P<number>[^']*)'\), currency='(?P<currency>[^']*)'"
)


_PARSER_REPRS = (
    (re.compile(r"(Duplicate cost: ')(?P<value>CompoundAmount\(.*\))('\.)\Z", re.DOTALL), "cost"),
    (
        re.compile(r"(Duplicate (?:metadata field on entry|posting metadata field): )(?P<value>KeyValue\(.*\))\Z"),
        "meta",
    ),
    (re.compile(r"(Tags or links not allowed after first Posting: )(?P<value>TagsLinks\(.*\))\Z"), "tags"),
    (re.compile(r"(Too many strings on transaction description: )(?P<value>\[.*\])\Z"), "strings"),
)


def readable_parser_message(message: str) -> str:
    """A parser diagnostic with the grammar value it quotes written as Beancount text.

    Upstream's grammar formats a `CompoundAmount`, `KeyValue`, `TagsLinks` or a
    list with `str()`, which is their repr: `Decimal('101.00')`,
    `datetime.date(2026, 1, 2)`, `links=set()` reached `check` details,
    strict-read refusals and the `add` posting refusal (w5/334). A message
    that does not parse as expected is returned unchanged.
    """
    for pattern, kind in _PARSER_REPRS:
        match = pattern.match(message)
        if match is None:
            continue
        value = match["value"]
        try:
            if kind == "cost":
                fields = dict(re.findall(r"(\w+)=(Decimal\('[^']*'\)|'[^']*'|None)", value))
                per, total = _repr_scalar(fields.get("number_per")), _repr_scalar(fields.get("number_total"))
                currency = _repr_scalar(fields.get("currency"))
                amounts = [part for part in (per, f"# {total}" if total else "", currency) if part]
                return f"{match[1]}{' '.join(amounts)}{match[3]}"
            if kind == "meta":
                key = re.match(r"KeyValue\(key='([^']*)', value=(.*)\)\Z", value, re.DOTALL)
                if key is None:
                    break
                return f"{match[1]}{key[1]}: {_repr_scalar(key[2])}"
            if kind == "tags":
                sets = re.match(r"TagsLinks\(tags=(.*), links=(.*)\)\Z", value, re.DOTALL)
                if sets is None:
                    break
                tags, links = (_repr_set(sets[1]), _repr_set(sets[2]))
                return match[1] + " ".join([*(f"#{tag}" for tag in tags), *(f"^{link}" for link in links)])
            strings = ast.literal_eval(value)
            return match[1] + " ".join(f'"{text}"' for text in strings)
        except (ValueError, SyntaxError, TypeError):
            break
    return message


def _repr_scalar(text: str | None) -> str:
    """One repr'd grammar value as ledger text: a number, an ISO date, a quoted string, TRUE/FALSE."""
    if text is None or text == "None":
        return ""
    decimal = re.fullmatch(r"Decimal\('([^']*)'\)", text)
    if decimal:
        return decimal[1]
    day = re.fullmatch(r"datetime\.date\((\d+), (\d+), (\d+)\)", text)
    if day:
        return f"{int(day[1]):04d}-{int(day[2]):02d}-{int(day[3]):02d}"
    if text in ("True", "False"):
        return text.upper()
    if text[:1] in "'\"":
        value = ast.literal_eval(text)
        return value if re.fullmatch(r"[A-Z][A-Z0-9'._-]*", value) else f'"{value}"'
    return text


def _repr_set(text: str) -> list[str]:
    return [] if text.strip() == "set()" else sorted(ast.literal_eval(text))


def _booking_message(error: Any, message: str) -> str:
    """Two lot-booking messages without the namedtuple reprs upstream formats them with.

    `No position matches` and `Cost is negative` print a whole `Posting` or
    `Cost` with `Decimal(...)`, `datetime.date(...)` and the posting's meta,
    whose line number points into an append that was never written (w5/333).
    Their siblings (`Not enough lots`, `Ambiguous matches`) already read as
    amounts; these now do too. Anything else passes through unchanged.
    """
    parsed = readable_parser_message(message)
    if parsed != message:
        return parsed
    currency = _BALANCE_CURRENCY.match(message)
    account = getattr(getattr(error, "entry", None), "account", None)
    if currency is not None and isinstance(account, str):
        # Upstream ends this with `: `, expecting the entry printed after it (w5/350).
        return f"Invalid currency {currency['currency']} for account '{account}': its open does not allow it."
    negative = _NEGATIVE_COST.match(message)
    if negative is not None:
        return f"Cost is negative: {negative['number']} {negative['currency']}"
    no_lot = _NO_LOT.match(message)
    if no_lot is None:
        return message
    from beancount.core.display_context import DisplayContext

    from bea_engine.ledger.writer import _cost_spec_text

    account, units = no_lot["account"], no_lot["units"].strip()
    postings = getattr(getattr(error, "entry", None), "postings", None) or []
    posting = next((p for p in postings if p.account == account and str(p.units) == units), None)
    cost = getattr(posting, "cost", None)
    requested = f"{units} {{{_cost_spec_text(cost, DisplayContext().build())}}}" if cost is not None else units
    return f"No position matches {requested} in {account}; it holds {no_lot['held'].strip()}"


def _plugin_message(message: str, ledger_file: Path | str | None, source: Any) -> str | None:
    """A plugin load failure as `file:line: Cannot ... plugin "name": cause`.

    The loader reports these against `<load>:0` with the traceback attached,
    so the directive's own line is found by scanning the ledger source — by
    name and, when the load recorded it, config — and the traceback's final
    exception block is kept as the cause.
    """
    from bea_engine.managed_load import PLUGIN_CONFIG_KEY

    config = source.get(PLUGIN_CONFIG_KEY, _UNKNOWN_CONFIG) if isinstance(source, dict) else _UNKNOWN_CONFIG
    match = _PLUGIN_FAILURE.match(message)
    if match is None:
        return None
    kind, name, traceback_text = match.groups()
    cause = _exception_summary(traceback_text)
    if kind == "importing":
        text = f'Cannot import plugin "{name}": {cause}. Check the name is spelled right and the plugin is installed.'
    else:
        text = f'Plugin "{name}" failed while running: {cause}.'
        if "required positional argument: 'config'" in cause:
            # Bundled plugins such as currency_accounts take a configuration
            # string, and the raw TypeError never said so (w5/400).
            text += f' This plugin needs a configuration string: plugin "{name}" "CONFIG".'
    location = _plugin_directive(ledger_file, name, config)
    if location is None:
        return f"<ledger>:0: {text}"
    return f"{location[0]}:{location[1]}: {text}"


_UNKNOWN_CONFIG = object()
_FRAME_LINE = re.compile(r'^(\s*)File "')


def _exception_summary(traceback_text: str) -> str:
    """The final exception of a formatted traceback: its type and whole message.

    The message may span lines (and carry notes), so the cause is everything
    after the last frame's source lines — not just the last non-empty line,
    which kept `Assets:Old -> ?` and dropped `ValueError: Bad account mapping:`
    (w1/101). Lines are joined with single spaces into one detail line.
    """
    lines = traceback_text.splitlines()
    start = 0
    frame_indent: int | None = None
    for index, line in enumerate(lines):
        match = _FRAME_LINE.match(line)
        if match:
            start, frame_indent = index + 1, len(match.group(1))
    if frame_indent is not None:
        # Skip the frame's source and caret lines, indented deeper than `File`.
        while start < len(lines) and (
            not lines[start].strip() or len(lines[start]) - len(lines[start].lstrip()) > frame_indent
        ):
            start += 1
    block = [line.strip() for line in lines[start:] if line.strip()]
    return " ".join(block) if block else traceback_text.strip()


def _plugin_directive(
    ledger_file: Path | str | None, name: str, config: Any = _UNKNOWN_CONFIG
) -> tuple[str, int] | None:
    """The `file, line` of the `plugin "name"` directive in the ledger source.

    With a known config, the directive carrying that config wins; the first
    directive naming the plugin is the fallback.
    """
    if ledger_file is None:
        return None
    directive = re.compile(rf"""^\s*plugin\s+"{re.escape(name)}"(?:\s+"((?:[^"\\]|\\.)*)")?""")
    try:
        # From bytes: `read_text` would turn a lone `\r` into an extra line.
        lines = Path(ledger_file).read_bytes().decode("utf-8", errors="replace").split("\n")
    except OSError:
        return None
    first: tuple[str, int] | None = None
    for lineno, line in enumerate(lines, start=1):
        match = directive.match(line)
        if match is None:
            continue
        first = first or (str(ledger_file), lineno)
        written = match.group(1)
        if config is not _UNKNOWN_CONFIG and (None if written is None else _unescape(written)) == config:
            return (str(ledger_file), lineno)
    return first


def _unescape(text: str) -> str:
    """A Beancount string body as the parser reads it: backslash escapes the next character."""
    return re.sub(r"\\(.)", r"\1", text)


def _duplicate_message(error: Any, message: str) -> str | None:
    """A duplicate report as one line: what repeats, and both locations.

    The loader message is `Duplicate entry: {txn} == {txn}` with two full
    reprs; the repeated transaction comes from the error's own entry and the
    original's location from the second repr, so no repr is ever displayed.
    """
    if not message.startswith("Duplicate entry: "):
        return None
    entry = getattr(error, "entry", None)
    if entry is None:
        return None
    locations = _TXN_LOCATION.findall(message)
    original = locations[-1] if len(locations) >= 2 else None
    source = getattr(error, "source", None) or {}
    filename = source.get("filename", "<ledger>")
    lineno = source.get("lineno", 0)
    summary = _entry_summary(entry)
    if original is None:
        return f"{filename}:{lineno}: Duplicate {summary}. Delete or change one of them."
    return (
        f"{filename}:{lineno}: Duplicate {summary}; "
        f"first entered at {original[0]}:{original[1]}. Delete or change one of them."
    )


def _entry_summary(entry: Any) -> str:
    """A transaction as `transaction on DATE "payee" "narration" (postings)`."""
    from beancount.core.data import Transaction
    from beancount.core.number import MISSING

    date = getattr(entry, "date", "?")
    if not isinstance(entry, Transaction):
        return f"{type(entry).__name__.lower()} on {date}"
    head = " ".join(f'"{text}"' for text in (entry.payee, entry.narration) if text)
    postings = []
    for posting in entry.postings:
        units: Any = posting.units
        if units is MISSING or getattr(units, "number", MISSING) is MISSING:
            postings.append(posting.account)
        else:
            # Fixed-point, as import rows are since w5/228: `str` gave `5.0E-7 BTC` (w5/383).
            postings.append(f"{posting.account} {format(units.number, 'f')} {units.currency}")
    legs = f" ({'; '.join(postings)})" if postings else ""
    words = f"transaction on {date}"
    if head:
        words += f" {head}"
    return words + legs


def result_context(rows: Any) -> Any:
    """A display context sized to these results rather than to the ledger's inputs."""
    from beancount.core.amount import Amount
    from beancount.core.display_context import DisplayContext
    from beancount.core.inventory import Inventory
    from beancount.core.position import Cost, Position

    digits_by_currency: dict[str, int] = {}

    def visit(value: Any) -> None:
        if isinstance(value, Amount | Cost):
            if isinstance(value.number, Decimal) and value.number.is_finite():
                digits_by_currency[value.currency] = max(
                    digits_by_currency.get(value.currency, 0), -int(value.number.as_tuple().exponent)
                )
        elif isinstance(value, Position):
            visit(value.units)
            visit(value.cost)
        elif isinstance(value, Mapping):
            for item in value.values():
                visit(item)
        elif isinstance(value, Inventory | list | tuple | set | frozenset):
            for item in value:
                visit(item)

    visit(rows)

    class ResultContext(DisplayContext):
        def quantize(self, number: Decimal, currency: str, precision: Any = None) -> Decimal:
            del precision  # Retain the upstream signature; result values determine display precision.
            # DisplayContext.quantize caps the integer portion at twelve
            # digits. Preserve large balances as well as fractional units.
            digits = -digits_by_currency.get(currency, 0)
            exponent = int(number.as_tuple().exponent)
            with localcontext() as arithmetic:
                arithmetic.prec = max(arithmetic.prec, len(number.as_tuple().digits) + max(0, exponent - digits))
                return number.quantize(Decimal(1).scaleb(digits))

    context = ResultContext()
    for currency, digits in digits_by_currency.items():
        # Every value in a currency receives the maximum precision present in
        # these results. Beanquery's per-column formatter can then neither
        # infer whole units from a majority nor discard calculated fractions.
        context.update(Decimal(1).scaleb(-digits), currency)
    return context
