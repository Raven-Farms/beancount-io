"""Load a ledger with its managed price includes resolved (w1/m29/t003).

One resolution step every load path shares: `check`, `list`, `query`,
`report`, `import`, and write validation all load through here, so no command
sees a different ledger than another. Ledgers without a managed include load
exactly as before — the wrapper detects that case from the include closure
and calls Beancount directly with zero overhead.

Python Beancount resolves includes as filesystem paths, so there is no file
map to overlay onto the way the hosted loader does (ADR 015 section 6).
Instead the wrapper stages a shadow of the include closure beside the
customer's files — the same beside-source staging write validation already
uses, so documents and plugins keep their paths — rewriting each managed
include line to the feed's effective file and loading the staged root. The
customer's files are never touched; entry and error filenames map back to
the originals before anything is returned, while feed entries keep their
cache paths the way hosted entries keep their virtual paths.

Precedence follows ADR 015 section 7 on the feed text: a managed point whose
date and pair collide with a ledger-authored price, directly or reciprocally,
is commented out with its metadata, keeping line numbers stable. The shadowed
count and the dates the engine sees travel in the per-source records for the
status view t004 builds; the effective text is cached per ledger and revision
so the portable export t005 builds reads the same bytes the load parsed.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import time
import unicodedata
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.request import OpenerDirector

from bea_engine.managed_price_cache import (
    CACHE_WRITE_PROBLEM,
    PriceFeedBlob,
    PriceFeedHead,
    ResolvedFeed,
    cache_root,
    cache_write_problem,
    feed_dir,
    freshness,
    resolve_feed,
    write_text_atomic,
)
from bea_engine.managed_prices import (
    DEFAULT_ORIGINS,
    MAX_URLS_PER_LOAD,
    AllowedUrl,
    ManagedPriceBudget,
    is_url_include_target,
    parse_managed_price_url,
)

if TYPE_CHECKING:
    from bea_engine.ledger.write import LedgerSnapshot

ORIGINS_ENV = "MANAGED_PRICE_ORIGINS"
"""Comma-separated origin allowlist, mirroring the hosted variable; empty disables."""

OFFLINE_ENV = "MANAGED_PRICE_OFFLINE"
"""Set to resolve managed includes from the cache only, without fetching."""

STRICT_ENV = "MANAGED_PRICE_STRICT"
"""Set to fail the load on a stale or unavailable managed source."""

# Beancount spells a date `YYYY-M-D` or `YYYY/M/D` (mixed separators, one or
# two digit month and day); feed dates are always ISO, so normalise before
# comparing.
_LEDGER_PRICE_RE = re.compile(
    r"^([0-9]{4})[-/]([0-9]{1,2})[-/]([0-9]{1,2})[ \t]+price[ \t]+([A-Z][A-Z0-9'._-]*)[ \t]+\S+[ \t]+"
    r"([A-Z][A-Z0-9'._-]*)",
    re.MULTILINE,
)
_METADATA_LINE_RE = re.compile(r"^[ \t]+[a-z][A-Za-z0-9_-]*\s*:")
_SHADOWED_LINE = "; shadowed by a ledger-authored price for the same date"
_ALREADY_INCLUDED_LINE = "; managed price feed already included from another file"
_NO_CACHED_REVISION = "no cached revision"
_OVER_LIMIT = (
    f"over the limit of {MAX_URLS_PER_LOAD} managed price sources per ledger load; "
    "remove a managed include to bring the ledger within it"
)


@dataclass(frozen=True)
class IncludeRef:
    """One include line that named a managed source, as written."""

    file: str
    line: int
    target: str


@dataclass(frozen=True)
class ManagedSource:
    """Per-source status threaded alongside the load, mirroring the hosted record."""

    url: str
    alias: str
    included_from: tuple[IncludeRef, ...]
    commodity: str | None
    quote: str | None
    source: str | None
    revision: str | None
    etag: str | None
    observed_at: str | None
    fetched_at: str | None
    next_refresh_at: str | None
    freshness: str
    error: str | None
    shadowed_count: int
    effective_dates: tuple[str, ...]
    effective_path: str | None = None
    effective_text: str | None = None


@dataclass(frozen=True)
class LoadedLedger:
    """A load with its managed sources: entries, errors, options, status."""

    entries: list[Any]
    errors: list[Any]
    options: dict[str, Any]
    sources: tuple[ManagedSource, ...] = ()


def collect_ledger_price_pairs(*texts: str) -> set[tuple[str, str, str]]:
    """Every `(date, base, quote)` the ledger's own files declare.

    Text-based like the hosted collector, so both engines shadow the same
    points: a price the ledger declares in any file wins regardless of
    include order.
    """
    pairs: set[tuple[str, str, str]] = set()
    for text in texts:
        for match in _LEDGER_PRICE_RE.finditer(text):
            year, month, day, base, quote = match.groups()
            try:
                when = date(int(year), int(month), int(day))
            except ValueError:
                continue  # Beancount rejects it too; nothing to shadow.
            pairs.add((when.isoformat(), base, quote))
    return pairs


@dataclass(frozen=True)
class EffectiveFeed:
    """A feed with ledger-shadowed points commented out, lines stable."""

    text: str
    shadowed_count: int
    effective_dates: tuple[str, ...]


def apply_ledger_price_precedence(
    text: str, prices: tuple[Any, ...], ledger_pairs: set[tuple[str, str, str]]
) -> EffectiveFeed:
    """Comment out managed points the ledger shadows, directly or reciprocally.

    Shadowed lines become comments with their metadata, so the line count is
    preserved and any diagnostic naming a virtual line still points at the
    right place in the feed revision.
    """
    lines = text.split("\n")
    effective_dates: list[str] = []
    shadowed = 0
    for price in prices:
        if (price.date, price.base, price.quote) in ledger_pairs or (
            price.date,
            price.quote,
            price.base,
        ) in ledger_pairs:
            shadowed += 1
            lines[price.line - 1] = _SHADOWED_LINE
            index = price.line
            while index < len(lines) and _METADATA_LINE_RE.match(lines[index]):
                lines[index] = f"; {lines[index].strip()}"
                index += 1
        else:
            effective_dates.append(price.date)
    return EffectiveFeed(
        text=text if shadowed == 0 else "\n".join(lines),
        shadowed_count=shadowed,
        effective_dates=tuple(effective_dates),
    )


def _env_origins() -> tuple[str, ...] | None:
    raw = os.environ.get(ORIGINS_ENV)
    if raw is None:
        return None
    return tuple(origin.strip() for origin in raw.split(",") if origin.strip())


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _iso(moment: float | None) -> str | None:
    if moment is None:
        return None
    return datetime.fromtimestamp(moment, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _holds(path: Path, text: str) -> bool:
    """Whether `path` already holds exactly `text` (unreadable reads as no)."""
    try:
        return path.read_text(encoding="utf-8") == text
    except (OSError, ValueError):
        return False


def _remap(value: str, staged: dict[str, str]) -> str:
    return staged.get(value, value)


def load_with_sources(
    entry: Path,
    *,
    offline: bool | None = None,
    strict: bool | None = None,
    origins: tuple[str, ...] | None = None,
    root: Path | None = None,
    now: float | None = None,
    opener: OpenerDirector | None = None,
    snapshot: LedgerSnapshot | None = None,
) -> LoadedLedger:
    """Load `entry` with managed price includes resolved, plus per-source status.

    Flags default from the `MANAGED_PRICE_*` environment; explicit arguments
    win. Without a managed include this is a plain Beancount load. Strict
    mode raises naming any stale or unavailable source; offline mode never
    fetches. A write snapshot may supply an absent included destination as an
    empty staged file, so reads and validation never need to create it.
    """
    from bea_engine import stopping

    # Beancount's parser swallows the exception a signal handler raises, so a
    # termination signal during the load exits at once instead (w1/074).
    with stopping.loading():
        return _load_with_sources(
            entry,
            offline=offline,
            strict=strict,
            origins=origins,
            root=root,
            now=now,
            opener=opener,
            snapshot=snapshot,
        )


def _load_with_sources(
    entry: Path,
    *,
    offline: bool | None,
    strict: bool | None,
    origins: tuple[str, ...] | None,
    root: Path | None,
    now: float | None,
    opener: OpenerDirector | None,
    snapshot: LedgerSnapshot | None,
) -> LoadedLedger:
    from beancount import loader
    from beancount.loader import LoadError

    from bea_engine.ledger.write import (
        LedgerSnapshot,
        is_candidate_file,
        keep_load_cache_private,
        refuse_cache_over_ledger,
    )
    from bea_engine.protocol import LedgerError

    keep_load_cache_private()
    _record_plugin_configs(loader)

    at = time.time() if now is None else now
    want_offline = _env_flag(OFFLINE_ENV) if offline is None else offline
    want_strict = _env_flag(STRICT_ENV) if strict is None else strict
    allowed_origins = _env_origins() if origins is None else origins
    if allowed_origins is None:
        allowed_origins = DEFAULT_ORIGINS
    cache = root or cache_root()

    snapshot = snapshot or LedgerSnapshot.capture(entry)
    refuse_cache_over_ledger(entry, snapshot.contents)
    managed = _collect_managed(snapshot, allowed_origins)
    if not managed and all(state is not None for state in snapshot.stats.values()):
        entries, errors, options = _load_fresh(entry, snapshot)
        _refuse_undecodable(errors, snapshot)
        return LoadedLedger(list(entries), list(errors), dict(options), ())

    # A source past the per-load cap is never fetched, and it is not dropped
    # either: left as written, Beancount read the URL as a file glob that
    # "does not match any files" at `<load>:0`, and `price export` judged the
    # ledger from the sixteen it had loaded (w5/190). It resolves as an
    # unavailable source whose cause is the limit, so the load error, `price
    # status` and the export all name it.
    budget = ManagedPriceBudget(limit=MAX_URLS_PER_LOAD)
    pending = managed
    resolved: dict[str, ResolvedFeed] = {}
    for source in pending:
        if not budget.claim(source.url):
            if want_strict:
                raise LedgerError(f"managed price source {source.url} is unavailable in strict mode: {_OVER_LIMIT}.")
            over_limit = PriceFeedHead(revision=None, next_refresh_at=0.0, last_error=_OVER_LIMIT)
            resolved[source.url] = ResolvedFeed(blob=None, head=over_limit)
            continue
        resolved[source.url] = resolve_feed(
            source.url,
            source.alias,
            root=cache,
            offline=want_offline,
            strict=want_strict,
            now=at,
            opener=opener,
        )
    blobs = {url: result.blob for url, result in resolved.items() if result.blob is not None}
    texts = [content.decode("utf-8", errors="replace") for content in snapshot.contents.values()]
    pairs = collect_ledger_price_pairs(*texts) if blobs else set()
    ledger_key = sha256(str(entry.resolve()).encode("utf-8")).hexdigest()[:16]
    # A staged write candidate is a fresh random file every time; caching its
    # effective text would leave one more full feed copy per write or preview.
    ephemeral = want_offline or is_candidate_file(entry)

    primary: set[tuple[str, int]] = set()
    for source in pending:
        if source.includes:
            first = source.includes[0]
            primary.add((first.file, first.line))

    cache_problems: dict[str, str] = {}
    with ExitStack() as stack:
        # Each feed's effective text is cached per (revision, ledger) so export
        # reads what the load parsed. Offline loads write nothing to the cache
        # (ADR 015 section 8), staged write candidates are not ledgers worth a
        # cache entry, and an unwritable cache degrades, so each of these stages
        # the text beside the ledger for this load only; its entries still
        # carry the cache path, like every other feed entry.
        effective: dict[str, tuple[PriceFeedBlob, EffectiveFeed, Path]] = {}
        staged_feeds: dict[str, str] = {}
        for url, blob in blobs.items():
            precedence = apply_ledger_price_precedence(blob.text, blob.feed.prices, pairs)
            path = feed_dir(url, cache) / f"{blob.revision}.effective.{ledger_key}.beancount"
            if not _holds(path, precedence.text):
                problem: str | None = None
                if not ephemeral:
                    try:
                        # Atomic: a concurrent load may be parsing this very file.
                        write_text_atomic(path, precedence.text)
                    except OSError as error:
                        problem = cache_write_problem(error, path)
                if ephemeral or problem is not None:
                    if problem is not None:
                        cache_problems[url] = problem
                    stand_in = stack.enter_context(_shadow(snapshot.root, precedence.text, entry, managed))
                    staged_feeds[str(stand_in)] = str(path)
                    effective[url] = (blob, precedence, stand_in)
                    continue
            effective[url] = (blob, precedence, path)

        staged = {path: stack.enter_context(_shadow(path, "", entry, managed)) for path in snapshot.contents}
        unavailable: list[Any] = []
        for path, original in snapshot.contents.items():
            content = _rewrite_includes(
                original,
                path,
                snapshot.patterns,
                staged,
                pending,
                resolved,
                effective,
                primary,
                unavailable,
                LoadError,
                stack,
            )
            staged[path].write_bytes(content)
        entries, errors, options = loader.load_file(str(staged[snapshot.root]))
        back = {str(staged_path): str(original) for original, staged_path in staged.items()}
        back.update(staged_feeds)
        entries = [_remap_entry(entry, back) for entry in entries]
        errors = [_remap_error(error, back) for error in errors]
    _refuse_undecodable(errors, snapshot)
    errors.extend(unavailable)

    for url, result in resolved.items():
        if result.head.last_error and result.head.last_error.startswith(CACHE_WRITE_PROBLEM):
            cache_problems.setdefault(url, result.head.last_error)
    for problem in sorted(set(cache_problems.values())):
        print(f"warning: {problem}; managed prices still load, but nothing was cached.", file=sys.stderr)

    sources: list[ManagedSource] = []
    for source in pending:
        result = resolved[source.url]
        serving = result.blob
        item = effective.get(source.url)
        applied = item[1] if item else None
        feed_path = item[2] if item else None
        sources.append(
            ManagedSource(
                url=source.url,
                alias=source.alias,
                included_from=tuple(source.includes),
                commodity=serving.feed.commodity if serving else None,
                quote=serving.feed.quote if serving else None,
                source=serving.feed.source if serving else None,
                revision=serving.revision if serving else None,
                etag=serving.etag if serving else None,
                observed_at=serving.feed.latest_observed_at if serving else None,
                fetched_at=_iso(serving.fetched_at) if serving else None,
                # A zero window is the "never fetched / refresh now" sentinel,
                # not a moment: report no scheduled refresh rather than 1970.
                next_refresh_at=_iso(result.head.next_refresh_at) if result.head.next_refresh_at > 0 else None,
                freshness=freshness(serving, at),
                # The same cause the load's unavailable-include error names.
                error=result.head.last_error
                or cache_problems.get(source.url)
                or (None if serving else _NO_CACHED_REVISION),
                shadowed_count=applied.shadowed_count if applied else 0,
                effective_dates=applied.effective_dates if applied else (),
                effective_path=_remap(str(feed_path), staged_feeds) if feed_path else None,
                effective_text=applied.text if applied else None,
            )
        )
    remapped_options = dict(options)
    if isinstance(remapped_options.get("filename"), str):
        remapped_options["filename"] = _remap(remapped_options["filename"], back)
    if isinstance(remapped_options.get("include"), list):
        remapped_options["include"] = [_remap(str(item), back) for item in remapped_options["include"]]
    return LoadedLedger(entries, errors, remapped_options, tuple(sources))


def _refuse_undecodable(errors: list[Any], snapshot: LedgerSnapshot) -> None:
    """Refuse a load whose error is a file that is not UTF-8, naming path, offset and remedy.

    The parser reports a string it cannot decode as an ordinary error at a
    line — `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9 in
    position 3` — so every read counted it among the ledger's errors and
    suggested `--allow-errors`, while `format` and `add` named the file, the
    byte and the fix (w5/278). Only a load that already holds that error is
    refused: bytes outside UTF-8 in a comment parse as they always did.
    """
    from bea_engine.ledger.text import decode_error_message
    from bea_engine.protocol import LedgerError

    contents = {os.path.normpath(path): content for path, content in snapshot.contents.items()}
    for error in errors:
        source = getattr(error, "source", None)
        if not isinstance(source, dict) or not str(getattr(error, "message", "")).startswith("UnicodeDecodeError:"):
            continue
        name = os.path.normpath(str(source.get("filename")))
        try:
            contents.get(name, b"").decode("utf-8")
        except UnicodeDecodeError as exc:
            raise LedgerError(decode_error_message(name, exc)) from exc


#: Source-meta key naming the config of the `plugin` directive whose run or
#: import failed. The loader reports every plugin failure against `<load>:0`
#: by name alone, so two directives naming one plugin with different configs
#: could not be told apart (w1/101).
PLUGIN_CONFIG_KEY = "__bea_plugin_config__"


def _record_plugin_configs(loader: Any) -> None:
    """Have the loader's plugin errors carry the failing directive's config.

    The loader builds those errors inside `run_transformations`, where the
    config is the `plugin_config` local. For the duration of that call only,
    `loader.LoadError` is a subclass that copies the local from the
    constructing frame into the error's source meta. Swapping it back
    afterwards keeps every pickle — Beancount's load cache — resolving the
    plain `LoadError`, so upstream tools can still read the cache.
    """
    if getattr(loader.run_transformations, "_bea_records_plugin_config", False):
        return
    base = loader.LoadError
    original = loader.run_transformations

    class _PluginAwareLoadError(base):  # type: ignore[misc,valid-type]
        def __new__(cls, source: Any, message: str, entry: Any = None) -> Any:
            caller = sys._getframe(1)
            if caller.f_code is original.__code__ and "plugin_config" in caller.f_locals:
                source = {**source, PLUGIN_CONFIG_KEY: caller.f_locals["plugin_config"]}
            return super().__new__(cls, source, message, entry)

        def __reduce__(self) -> Any:
            return (base, tuple(self))

    def run_transformations(*args: Any, **kwargs: Any) -> Any:
        loader.LoadError = _PluginAwareLoadError
        try:
            return original(*args, **kwargs)
        finally:
            loader.LoadError = base

    run_transformations._bea_records_plugin_config = True  # type: ignore[attr-defined]
    loader.run_transformations = run_transformations


def _load_fresh(entry: Path, snapshot: LedgerSnapshot) -> tuple[Any, Any, Any]:
    """`loader.load_file`, refusing a pickle-cache hit that misses files now on disk.

    Beancount's cache keys on the mtime and size of the files the cached load
    read, so a file that newly matches an include glob, or a missing include
    that now exists, never invalidates it (w1/083). The snapshot has already
    expanded every include on disk; when it holds a file the cached load never
    read, the cache is stale — drop it and load again.

    Nor is an attachment among those files, though the load judged whether each
    `document` file exists and listed what a `documents` root holds. A cached
    answer that no longer matches the disk is dropped the same way (w5/116).

    And the loader fingerprints the files only after it has parsed them, so a
    write that lands while a slow load runs is cached as the old entries under
    the new fingerprint, which every later read then trusts: the transaction
    was in the file and missing from `balance`, `list` and `query`, and an
    import wrote it again (w5/218). The snapshot's stats predate the load; a
    file that no longer matches them means the load overlapped a change, so
    its cache is not kept and the next read parses the files as they are.

    Nor does the cache say who loaded it. `bean-check`, `bean-doctor` and an
    editor's own Beancount read the bytes as they are, so a cache they wrote
    still holds a decomposed payee, a BOM's syntax error and plugin errors
    without their configs; served here, an NFC literal stopped matching until
    a ledger file changed (w5/220). Only a cache this function wrote is trusted.
    """
    from beancount import loader

    from bea_engine.ledger.write import pickle_cache_of

    cache = pickle_cache_of(entry)
    if cache.is_file() and not _engine_wrote(cache):
        cache.unlink(missing_ok=True)
    cached = cache.exists()
    entries, errors, options = loader.load_file(str(entry))
    if cached:
        read = {os.path.normpath(name) for name in options.get("include") or ()}
        on_disk = {os.path.normpath(path) for path in snapshot.contents}
        if not on_disk <= read or _documents_moved(entries, errors, options):
            cache.unlink(missing_ok=True)
            entries, errors, options = loader.load_file(str(entry))
    if _changed_since(snapshot):
        cache.unlink(missing_ok=True)
    _mark_engine_cache(cache)
    return entries, errors, options


def _changed_since(snapshot: LedgerSnapshot) -> bool:
    """Whether any file of the snapshot differs on disk from the stat it was captured with."""
    for path, before in snapshot.stats.items():
        try:
            current = path.stat()
        except OSError:
            return True
        if before is None or (current.st_ino, current.st_mtime_ns, current.st_size) != (
            before.st_ino,
            before.st_mtime_ns,
            before.st_size,
        ):
            return True
    return False


#: What ends a load cache `_load_fresh` wrote. Unpickling stops at the pickle's
#: own end, so upstream tools read a marked cache exactly as they did, and one
#: they write themselves replaces the file, mark included.
_ENGINE_CACHE_MARK = b"\nbea-engine-load\n"


def _engine_wrote(cache: Path) -> bool:
    """Whether a load cache ends with the mark of this module's own load."""
    try:
        with cache.open("rb") as stream:
            stream.seek(-len(_ENGINE_CACHE_MARK), os.SEEK_END)
            return stream.read() == _ENGINE_CACHE_MARK
    except OSError:
        return False


def _mark_engine_cache(cache: Path) -> None:
    """Mark the cache the load just made, if it was slow enough to leave one."""
    if not cache.is_file() or _engine_wrote(cache):
        return
    try:
        with cache.open("ab") as stream:
            stream.write(_ENGINE_CACHE_MARK)
    except OSError:
        # Unmarked, it is loaded again next time rather than trusted.
        pass


def _documents_moved(entries: Any, errors: Any, options: Any) -> bool:
    """Whether a load's document findings disagree with the files on disk now.

    True when a `document` file's existence differs from what the load
    reported, or a `documents` root would yield a file or an error the load
    does not hold. A load made just now always answers False.
    """
    from beancount.core import getters
    from beancount.core.data import Document
    from beancount.ops import documents

    declared = {item.filename for item in entries if isinstance(item, Document)}
    findings = [error for error in errors if isinstance(error, documents.DocumentError)]
    reported = {error.entry.filename for error in findings if isinstance(error.entry, Document)}
    if reported != {name for name in declared | reported if not os.path.exists(name)}:
        return True
    roots = options.get("documents")
    if not roots:
        return False
    accounts = getters.get_accounts(entries)
    problems: set[str] = set()
    for directory in map(os.path.normpath, roots):
        found, root_errors = documents.find_documents(  # type: ignore[no-untyped-call]
            directory, options["filename"], accounts
        )
        if not {item.filename for item in found} <= declared:
            return True
        problems.update(error.message for error in root_errors)
    return problems != {error.message for error in findings if error.entry is None}


@dataclass
class _PendingSource:
    url: str
    alias: str
    includes: list[IncludeRef]


def _collect_managed(snapshot: Any, origins: tuple[str, ...]) -> list[_PendingSource]:
    """Group the closure's allowed managed includes by canonical feed URL.

    Disallowed URLs are left for Beancount to report, exactly as today.
    Nested includes, globs, and cycles are already handled by the snapshot's
    closure walk. The per-load cap applies later, when the budget claims;
    a source past it stays in the list and resolves as unavailable.
    """
    from bea_engine.ledger.text import iter_includes

    by_url: dict[str, _PendingSource] = {}
    for path, content in snapshot.contents.items():
        for span in iter_includes(content):
            if not is_url_include_target(span.target):
                continue
            decision = parse_managed_price_url(span.target, origins)
            if not isinstance(decision, AllowedUrl):
                continue
            include = IncludeRef(file=str(path), line=span.line, target=span.target)
            existing = by_url.get(decision.url)
            if existing is not None:
                existing.includes.append(include)
            else:
                by_url[decision.url] = _PendingSource(url=decision.url, alias=decision.alias, includes=[include])
    return list(by_url.values())


@contextmanager
def _shadow(path: Path, content: str, entry: Path, managed: list[_PendingSource]) -> Iterator[Path]:
    """A staged copy beside `path` for this load, with a refusal that describes a read.

    Resolving a managed price include parses shadow copies of the closure, each
    beside its source so relative paths keep their meaning. In a read-only
    directory that failed with the write path's message — "bea validates a
    write on a staged copy…" — on `list`, `check` and `balance`, commands that
    write nothing (w5/095). A load that is itself validating a write keeps
    that message; a read says what it needed the directory for and why.
    """
    from bea_engine.ledger.write import candidate_file, is_candidate_file
    from bea_engine.protocol import AuthError

    with ExitStack() as stack:
        try:
            staged = stack.enter_context(candidate_file(path, content))
        except AuthError as exc:
            if is_candidate_file(entry):
                raise
            includes = ", ".join(sorted({source.url for source in managed})) or "a managed price include"
            raise AuthError(
                f"Cannot read {entry}: its managed price include ({includes}) is resolved on a temporary copy "
                f"beside each ledger file, and the directory {path.parent} is not writable. Make that directory "
                "writable, or read a snapshot made with bea price export, which needs no temporary copy. "
                "Nothing was changed."
            ) from exc
        yield staged


def _rewrite_includes(
    original: bytes,
    path: Path,
    patterns: dict[str, tuple[Path, ...]],
    staged: dict[Path, Path],
    pending: list[_PendingSource],
    resolved: dict[str, Any],
    effective: dict[str, tuple[PriceFeedBlob, EffectiveFeed, Path]],
    primary: set[tuple[str, int]],
    unavailable: list[Any],
    load_error: Any,
    stack: ExitStack,
) -> bytes:
    """Rewrite one closure file's includes for its staged twin.

    Local includes expand to staged paths like write validation does; the
    first managed include per URL points at its effective feed file while
    repeat occurrences become placeholders, so the same URL included twice
    never multiplies entries. An unresolvable managed include becomes an
    unavailable comment with a loader error naming the include as written,
    its file and line, and the cause. Anything else stays byte-identical.
    """
    from bea_engine.ledger.text import iter_includes
    from bea_engine.ledger.write import literal_include, staged_include

    by_target = {include.target: source for source in pending for include in source.includes}
    content = original
    for span in sorted(iter_includes(content), key=lambda item: item.start, reverse=True):
        source = by_target.get(span.target)
        if source is None:
            matches = patterns.get(str(path.parent / span.target), ())
            if matches:
                # One line stays one line, so every later line of this file
                # keeps its number (w5/092, the read twin of w5/079).
                replacement = staged_include(stack, path, [staged[p] for p in matches])
                content = content[: span.start] + replacement.encode() + content[span.end :]
            continue
        result = resolved.get(source.url)
        blob = result.blob if result is not None else None
        if blob is not None:
            if (str(path), span.line) in primary:
                _, _, feed_path = effective[source.url]
                replacement = literal_include(feed_path)
                content = content[: span.start] + replacement.encode() + content[span.end :]
            else:
                content = _swap_line(content, span.line, f"{_ALREADY_INCLUDED_LINE}\n".encode())
            continue
        cause = ((result.head.last_error if result is not None else None) or _NO_CACHED_REVISION).rstrip()
        comment = f"; managed price source unavailable: {span.target} ({cause})\n".encode()
        content = _swap_line(content, span.line, comment)
        unavailable.append(
            load_error(
                {"filename": str(path), "lineno": span.line},
                f'managed price source unavailable: include "{span.target}" in {path}:{span.line}: '
                f"{cause.rstrip('.')}. "
                "Run bea price status to inspect the source.",
            )
        )
    return content


def _swap_line(content: bytes, line: int, replacement: bytes) -> bytes:
    """Replace 1-based `line` keeping the line count, so later spans stay valid."""
    rows = content.splitlines(keepends=True)
    start = sum(len(row) for row in rows[: line - 1])
    return content[:start] + replacement + content[start + len(rows[line - 1]) :]


def _remap_entry(entry: Any, back: dict[str, str]) -> Any:
    """Name the original file wherever an entry — or one of its postings — names a staged twin.

    A posting carries its own source location, and Beanquery's postings table
    reads `filename` from it. Left on the staged copy, `SELECT filename` named
    a `.bea-*.tmp` file that changed every run and was gone when the command
    returned, so a query filtering or grouping by source file silently matched
    nothing (w5/099).
    """
    postings = getattr(entry, "postings", None)
    if postings:
        remapped = [_remap_meta(posting, back) for posting in postings]
        if any(new is not old for new, old in zip(remapped, postings, strict=True)):
            entry = entry._replace(postings=remapped)
    return _remap_meta(entry, back)


def _remap_meta(item: Any, back: dict[str, str]) -> Any:
    meta = getattr(item, "meta", None)
    if not isinstance(meta, dict) or "filename" not in meta:
        return item
    mapped = _remap(str(meta["filename"]), back)
    if mapped == meta["filename"]:
        return item
    return item._replace(meta={**meta, "filename": mapped})


def _remap_error(error: Any, back: dict[str, str]) -> Any:
    source = getattr(error, "source", None)
    if not isinstance(source, dict) or "filename" not in source:
        return error
    mapped = _remap(str(source["filename"]), back)
    message = getattr(error, "message", "")
    for staged_path, original in back.items():
        message = message.replace(staged_path, original)
    if mapped == source["filename"] and message == getattr(error, "message", ""):
        return error
    replaced = dict(source)
    replaced["filename"] = mapped
    try:
        return error._replace(source=replaced, message=message)
    except (AttributeError, TypeError, ValueError):
        return error


def source_json(source: ManagedSource) -> dict[str, Any]:
    """One managed source as the status record ADR 015 section 8 describes."""
    return {
        "url": source.url,
        "alias": source.alias,
        "included_from": [
            {"file": include.file, "line": include.line, "target": include.target} for include in source.included_from
        ],
        "commodity": source.commodity,
        "quote": source.quote,
        "source": source.source,
        "revision": source.revision,
        "etag": source.etag,
        "observed_at": source.observed_at,
        "fetched_at": source.fetched_at,
        "next_refresh_at": source.next_refresh_at,
        "freshness": source.freshness,
        "error": source.error,
        "shadowed_count": source.shadowed_count,
        "effective_dates": list(source.effective_dates),
    }


def names_managed_source(entry: Path) -> bool:
    """Whether the include closure of `entry` holds a managed price include.

    For a caller that runs upstream's own command and must decide whether its
    plain load would see the ledger every other command sees. A closure that
    cannot be read answers no, leaving that failure to the load itself.
    """
    from bea_engine.ledger.write import LedgerSnapshot
    from bea_engine.protocol import EngineError

    origins = _env_origins()
    try:
        snapshot = LedgerSnapshot.capture(entry)
    except (OSError, EngineError):
        return False
    return bool(_collect_managed(snapshot, DEFAULT_ORIGINS if origins is None else origins))


def load_file(
    entry: Path | str,
    *,
    offline: bool | None = None,
    strict: bool | None = None,
    origins: tuple[str, ...] | None = None,
    root: Path | None = None,
    now: float | None = None,
    opener: OpenerDirector | None = None,
    snapshot: LedgerSnapshot | None = None,
) -> tuple[list[Any], list[Any], dict[str, Any]]:
    """Drop-in `loader.load_file` with managed includes resolved.

    For call sites that need the per-source records, `load_with_sources`
    returns them alongside.
    """
    loaded = load_with_sources(
        Path(entry),
        offline=offline,
        strict=strict,
        origins=origins,
        root=root,
        now=now,
        opener=opener,
        snapshot=snapshot,
    )
    if loaded.sources:
        loaded.options["bea_managed_price_sources"] = [source_json(source) for source in loaded.sources]
    return loaded.entries, loaded.errors, loaded.options


@dataclass(frozen=True)
class PortableExport:
    """A self-contained copy of the ledger with local price files."""

    output: Path
    files: tuple[str, ...]
    sources: tuple[ManagedSource, ...]
    errors: list[Any]
    overwritten: tuple[str, ...] = ()


def export_portable(
    entry: Path,
    output: Path | None = None,
    *,
    allow_errors: bool = False,
    force: bool = False,
    offline: bool | None = None,
    strict: bool | None = None,
    origins: tuple[str, ...] | None = None,
    root: Path | None = None,
    now: float | None = None,
    opener: OpenerDirector | None = None,
) -> PortableExport:
    """Snapshot the ledger with local price files and relative includes.

    Each managed feed lands at `prices/<ALIAS>.beancount` under the output
    directory as a `custom "bea-managed-source"` marker directive plus the
    exact effective text the load parsed, so the next pipeline stage replays
    the mapping and stock Beancount checks the tree untouched. An unavailable
    source refuses the export naming it, unless `allow_errors` carries the
    marker alone.
    """
    from bea_engine.ledger.write import LedgerSnapshot
    from bea_engine.protocol import AuthError, LedgerError, UsageError

    loaded = load_with_sources(
        entry, offline=offline, strict=strict, origins=origins, root=root, now=now, opener=opener
    )
    failed = [source for source in loaded.sources if source.revision is None]
    if failed and not allow_errors:
        names = ", ".join(f"{source.alias} ({source.url})" for source in failed)
        raise UsageError(
            f"Cannot export: managed price source {names} is unavailable. "
            "Retry, or pass --allow-errors to export with its marker only."
        )
    target = (output or entry.parent / f"{entry.stem}-export").expanduser()
    snapshot = LedgerSnapshot.capture(entry)
    # `resolve()` for a destination that does not exist yet, too: `absolute()`
    # leaves `..` in place, so `books/not-created/..` compared unequal to
    # `books` and slipped past the guard below — then `mkdir(parents=True)`
    # created the missing component and the writes followed `..` straight back
    # into the ledger, rewriting the customer's own `main.bean`.
    #
    # `resolve()` is the right tool rather than stripping `..` textually: it
    # resolves symlinks in the ancestors that do exist *and* normalizes the
    # rest, so a destination reached through a symlinked parent is compared as
    # the directory it truly names.
    resolved_target = target.resolve()
    for path in snapshot.contents:
        if resolved_target == path.parent.resolve():
            raise UsageError(
                f"Cannot export into {target}: it holds {path.name}, which the export would overwrite. "
                "Choose an empty or dedicated directory."
            )
    destinations: dict[Path, Path] = {}
    external = 0
    # Classified by the file each path truly names. Snapshot paths keep a
    # lexical `..` (`books/../shared/accounts.bean`), which `relative_to`
    # accepted as `../shared/accounts.bean`: the copy was written beside the
    # export instead of in it, over whatever lived there, and the include kept
    # pointing outside the snapshot.
    home = snapshot.root.parent.resolve()
    for path in snapshot.contents:
        if path == snapshot.root:
            # The root keeps its own name even when it is a link elsewhere.
            destinations[path] = target / path.name
            continue
        try:
            destinations[path] = target / path.resolve().relative_to(home)
        except ValueError:
            external += 1
            destinations[path] = target / "_shared" / f"{external:02d}-{path.name}"
    # The resolved file decides containment, but not how many files there are.
    # `a.bean` and `b.bean` linked to one `tx.bean` are two includes the loader
    # reads twice; both resolved to `tx.bean`, so the export wrote one file,
    # pointed both includes at it, and stock Beancount refused the snapshot as
    # a duplicate filename with half the transactions. Each alias keeps the
    # name the ledger spells when that stays inside the export.
    sharing: dict[Path, list[Path]] = {}
    for path, dest in destinations.items():
        sharing.setdefault(dest, []).append(path)
    claimed = set(sharing)
    lexical_home = Path(os.path.normpath(snapshot.root.parent))
    for dest, paths in sharing.items():
        for path in paths if len(paths) > 1 else ():
            spelled = Path(os.path.normpath(path))
            own = target / spelled.relative_to(lexical_home) if spelled.is_relative_to(lexical_home) else None
            if own == dest:
                continue
            if own is None or own in claimed:
                external += 1
                own = target / "_shared" / f"{external:02d}-{path.name}"
            destinations[path] = own
            claimed.add(own)
    # Allocated against the copied files, not independently of them. A ledger
    # may legitimately keep its own `prices/BTC-USD.beancount` beside a managed
    # `BTC-USD` feed; the two maps used to be built in isolation, so the feed
    # wrote straight over the copy — the manual price vanished and the snapshot
    # included one file twice. The copies keep their relative paths, because
    # that is what makes the export portable, so the generated file is the one
    # that moves.
    taken = set(destinations.values())
    # The directory moves for the same reason. An included file literally named
    # `prices` is copied to `prices`, where the feeds wanted a directory: the
    # copy was written, then `mkdir` died on a raw `FileExistsError` (w5/191).
    feed_dir = _free_feed_directory(target, taken)
    feed_files: dict[str, Path] = {}
    for source in loaded.sources:
        feed_files[source.url] = _free_feed_path(feed_dir, source.alias, taken)
        taken.add(feed_files[source.url])
    by_target = {
        include.target: feed_files[source.url] for source in loaded.sources for include in source.included_from
    }
    repeats = {
        (include.target, include.file, include.line)
        for source in loaded.sources
        for include in source.included_from[1:]
    }
    # Checked as a whole plan before the first write. A destination that is
    # already one of the ledger's own files — through a symlink, or a hard
    # link no path comparison can see — would be written straight through
    # into the books, so identity is compared, not spelling.
    attachments = _export_attachments(loaded, snapshot, destinations, target, home)
    attachments.update(_export_plugin_modules(loaded, snapshot, target))
    planned = [*destinations.values(), *feed_files.values(), *attachments]
    for dest in planned:
        if not dest.exists():
            continue
        for ledger_file in [*snapshot.contents, *attachments.values()]:
            if os.path.samefile(dest, ledger_file):
                raise UsageError(
                    f"Cannot export: {dest} is the source file {ledger_file} (a link to it), "
                    "which the export would overwrite. Choose an empty or dedicated directory. "
                    "Nothing was written."
                )
    # Nor may a planned file land where one of the ledger's own include globs
    # would read it back: the snapshot would silently join the books (w5/072).
    from bea_engine.ledger.write import _included_new_file

    for dest in planned:
        claimed_by = next((p for p in snapshot.patterns if _included_new_file(dest.resolve(), p)), None)
        if claimed_by is not None and not dest.exists():
            raise UsageError(
                f"Cannot export: {dest} would become part of the ledger being exported — its include pattern "
                f"{claimed_by} matches that path. Choose a directory outside the ledger's includes. "
                "Nothing was written."
            )
    # And an export writes inside the directory it was given, or nowhere.
    for dest in planned:
        if not dest.resolve().is_relative_to(resolved_target):
            raise UsageError(f"Cannot export: {dest} would land outside {target}. Nothing was written.")
    # The directories the plan needs are part of the plan. A regular file at
    # `output/sub` passed every check above while `output/sub/accounts.bean`
    # was planned, so the root was copied before `mkdir` failed on the include
    # and the export left half a ledger behind. `--force` replaces files the
    # export writes; it does not remove what stands where a directory must be.
    for dest in planned:
        blocker = _destination_blocker(dest)
        if blocker is not None:
            needs = "a file" if blocker == dest else "a directory"
            raise UsageError(
                f"Cannot export into {target}: {blocker} is in the way of {dest}, where the export needs {needs}. "
                "Move it or choose another directory; --force does not remove it. Nothing was written."
            )
    # The plan is checked against itself as well as the disk: one planned file
    # standing where another needs a directory (an included file named
    # `_shared` beside an include from outside the tree) is on no disk yet, so
    # the loop above passes it and the second write fails after the first.
    files = set(planned)
    for dest in planned:
        inside = next((parent for parent in dest.parents if parent in files), None)
        if inside is not None:
            raise UsageError(
                f"Cannot export into {target}: the export would write {inside} as a file and {dest} inside it. "
                f"Rename the ledger file that becomes {inside.name}. Nothing was written."
            )
    # A file already at a planned destination is a file the export was never
    # given: the directory the user picked may be somebody else's ledger, and
    # replacing it reported success. Re-exporting into a previous snapshot is
    # the deliberate case, so `--force` is the way past it.
    existing = [dest for dest in planned if dest.exists() or dest.is_symlink()]
    if existing and not force:
        first = min(existing, key=lambda dest: str(dest))
        more = f" ({len(existing)} files in all)" if len(existing) > 1 else ""
        raise UsageError(
            f"Cannot export into {target}: it already holds {first}, which the export would overwrite{more}. "
            "Choose an empty or dedicated directory, or pass --force to overwrite. Nothing was written."
        )
    # Whether the filesystem will take the plan is part of the plan too. A
    # read-only directory surfaced as a raw `PermissionError: [Errno 13]` from
    # the first `mkdir`, with exit 1 as if the ledger had failed validation; it
    # is the filesystem refusing (exit 3), said before anything is written
    # (w5/279).
    for dest in planned:
        if dest.is_file() and not os.access(dest, os.W_OK):
            raise AuthError(
                f"Cannot export into {target}: {dest} is read-only and cannot be replaced. Nothing was written."
            )
        holder = next((parent for parent in dest.parents if parent.is_dir()), None)
        if not dest.exists() and holder is not None and not os.access(holder, os.W_OK | os.X_OK):
            raise AuthError(
                f"Cannot export into {target}: the directory {holder.resolve()} is not writable. Nothing was written."
            )
    written: list[str] = []
    at = time.time() if now is None else now
    try:
        for path, original in snapshot.contents.items():
            dest = destinations[path]
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(
                _rewrite_export_includes(original, path, snapshot.patterns, destinations, by_target, repeats)
            )
            written.append(str(dest))
        for dest, document in attachments.items():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(document, dest)
            written.append(str(dest))
        for source in loaded.sources:
            dest = feed_files[source.url]
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(_export_feed_text(source, at), encoding="utf-8")
            written.append(str(dest))
    except OSError as exc:
        # The checks above cannot see everything (a full disk, a directory
        # locked mid-run), so a failed write still says how far it got.
        done = (
            f"{len(written)} of {len(planned)} files were already written ({', '.join(sorted(written))}); "
            "the export is incomplete."
            if written
            else "Nothing was written."
        )
        error = AuthError if isinstance(exc, PermissionError) else LedgerError
        raise error(
            f"Cannot export into {target}: writing {dest} failed ({exc.strerror or type(exc).__name__}). {done}"
        ) from exc
    return PortableExport(
        output=target,
        files=tuple(sorted(written)),
        sources=loaded.sources,
        errors=list(loaded.errors),
        overwritten=tuple(sorted(str(dest) for dest in existing)),
    )


def _destination_blocker(dest: Path) -> Path | None:
    """The existing path that stops `dest` from being written as a file, if any.

    Either `dest` itself is a directory, or its nearest existing ancestor is
    something other than a directory.
    """
    if dest.is_dir():
        return dest
    for ancestor in dest.parents:
        if ancestor.is_dir():
            return None
        if ancestor.exists() or ancestor.is_symlink():
            return ancestor
    return None


def _export_attachments(
    loaded: LoadedLedger,
    snapshot: LedgerSnapshot,
    destinations: dict[Path, Path],
    target: Path,
    home: Path,
) -> dict[Path, Path]:
    """Where each `document` the ledger names goes in the export.

    Beancount checks that a document exists, so an export that copied only the
    ledger text failed stock `bean-check` for a source that passed it. A file
    under the root's directory is copied to the same relative place, which
    keeps every relative `document` path — and a relative `documents` option —
    resolving as before. What cannot travel that way is refused before
    anything is written rather than left pointing back at this machine: a
    file outside that tree, an absolute path in the directive, or a directive
    in an included file that the export relocates. So is a document whose
    file is not there at all, with or without `allow_errors`.
    """
    from beancount.core.data import Document

    from bea_engine.protocol import UsageError

    contents = snapshot.contents
    ledger_files = {path.resolve(): path for path in contents}
    unsupported: list[str] = []
    for option_dir in loaded.options.get("documents") or []:
        if os.path.isabs(option_dir):
            unsupported.append(f'option "documents" "{option_dir}" (absolute)')
    # Keyed by destination, valued by the file to copy. The destination keeps
    # the path exactly as the directive spells it: a symlink (`alias.pdf ->
    # receipt.pdf`, or a symlinked folder `linked/`) used to be resolved
    # first, so the export copied `receipt.pdf` while the copied ledger still
    # named `alias.pdf`, and two aliases of one receipt collapsed into a
    # single copy that neither name reached. The resolved file still decides
    # containment and what bytes travel; the copy is a plain file.
    attachments: dict[Path, Path] = {}
    # Beancount reports a `document` whose file is absent as a load error and
    # keeps the entry, so the plan held a source that was not there: the ledger
    # was written, then the copy died on a raw `FileNotFoundError` (w5/117).
    missing: list[str] = []
    for entry in loaded.entries:
        if not isinstance(entry, Document):
            continue
        document = Path(entry.filename).resolve()
        if not document.is_file():
            where = f"{Path(str(entry.meta.get('filename', ''))).name}:{int(entry.meta.get('lineno') or 0)}"
            missing.append(f"{document} (named by {where})")
            continue
        try:
            canonical = target / document.relative_to(home)
        except ValueError:
            unsupported.append(f"{document} (outside {home})")
            continue
        named_by = str(entry.meta.get("filename", ""))
        ledger = ledger_files.get(Path(named_by).resolve()) if named_by else None
        if ledger is None:
            attachments[canonical] = document
            continue
        line = int(entry.meta.get("lineno") or 0)
        lines = contents[ledger].decode("utf-8", "replace").split("\n")
        text = lines[line - 1] if 0 < line <= len(lines) else ""
        quoted = text.split('"')[1] if text.count('"') >= 2 else ""
        # Beancount joins a relative name onto its file's directory and
        # normalizes lexically, both here and when checking the export, so
        # the same relative spelling from the copied ledger is what must exist.
        spelled = os.path.relpath(os.path.normpath(entry.filename), os.path.dirname(os.path.abspath(named_by)))
        dest = Path(os.path.normpath(destinations[ledger].parent / spelled))
        try:
            relocated = ledger != snapshot.root and destinations[ledger] != target / ledger.resolve().relative_to(home)
        except ValueError:
            relocated = True
        if os.path.isabs(quoted) or relocated or not dest.is_relative_to(target):
            unsupported.append(f"{document} (named by {ledger.name}:{line})")
            continue
        attachments[dest] = document
    if missing:
        raise UsageError(
            "Cannot export: these document attachments do not exist as files: "
            + "; ".join(missing)
            + ". Restore them or remove the directives. Nothing was written."
        )
    if unsupported:
        raise UsageError(
            "Cannot export: these document attachments would not travel with the export: "
            + "; ".join(unsupported)
            + ". Keep documents beside the ledger and name them by relative path. Nothing was written."
        )
    return attachments


def _export_plugin_modules(loaded: LoadedLedger, snapshot: LedgerSnapshot, target: Path) -> dict[Path, Path]:
    """Where each plugin module that lives beside the ledger goes in the export.

    `option "insert_pythonpath"` puts the root's directory on the module path,
    so `plugin "myplug"` may name a `myplug.py` — or a package — sitting next
    to `main.bean`. The export copied the ledger text and not the module, so
    it reported success for a snapshot stock `bean-check` could not load
    (w5/094). Such a module travels to the same relative place, where the
    copied option finds it again; a plugin installed elsewhere is not the
    export's to carry. Keyed by destination like the document attachments,
    so the same collision and overwrite rules apply.
    """
    if not loaded.options.get("insert_pythonpath"):
        return {}
    home = snapshot.root.parent
    modules: dict[Path, Path] = {}
    for name, _config in loaded.options.get("plugin") or []:
        top = str(name).split(".", 1)[0]
        module, package = home / f"{top}.py", home / top
        if package.is_dir():
            sources = [path for path in sorted(package.rglob("*.py")) if "__pycache__" not in path.parts]
        elif module.is_file():
            sources = [module]
        else:
            continue
        for source in sources:
            modules[target / source.relative_to(home)] = source
    return modules


def _free_feed_directory(target: Path, taken: set[Path]) -> Path:
    """The directory the generated feeds go in: `prices`, unless a copied file has that name.

    Deterministic like the feed names: `prices`, then `prices-managed`, then numbered.
    """
    owned = {_name_key(path) for path in taken}
    candidate = target / "prices"
    suffix = 0
    while _name_key(candidate) in owned:
        suffix += 1
        candidate = target / ("prices-managed" if suffix == 1 else f"prices-managed-{suffix}")
    return candidate


def _free_feed_path(directory: Path, alias: str, taken: set[Path]) -> Path:
    """Where a generated feed goes, never over a path something else owns.

    Deterministic, so re-exporting the same tree produces the same names: the
    plain `<alias>.beancount` when it is free, then `-managed`, then numbered.
    """
    # Compared as a case-insensitive, normalization-insensitive volume compares
    # names — the macOS default. `prices/btc-usd.beancount` and the `BTC-USD`
    # feed's file are one file there, and an exact-path test let the feed text
    # replace the copy (w5/189). Folded on every platform, so the names do not
    # depend on where the export ran and the snapshot survives moving.
    owned = {_name_key(path) for path in taken}
    candidate = directory / f"{alias}.beancount"
    suffix = 0
    while _name_key(candidate) in owned:
        suffix += 1
        stem = f"{alias}-managed" if suffix == 1 else f"{alias}-managed-{suffix}"
        candidate = directory / f"{stem}.beancount"
    return candidate


def _name_key(path: Path) -> str:
    """One key for every spelling a case-insensitive volume reads as `path`."""
    return unicodedata.normalize("NFC", unicodedata.normalize("NFD", str(path)).casefold())


def _rewrite_export_includes(
    original: bytes,
    path: Path,
    patterns: dict[str, tuple[Path, ...]],
    destinations: dict[Path, Path],
    by_target: dict[str, Path],
    repeats: set[tuple[str, str, int]],
) -> bytes:
    """Rewrite one copied file's includes as portable relative targets.

    Local includes follow their files to the new tree, managed URLs become
    the sibling price files — the first include of each feed; a repeat becomes
    a comment on its own line, as the load treats it — and anything the loader
    left unresolved stays byte-identical so stock tools report it the same way.
    """
    from bea_engine.ledger.text import iter_includes
    from bea_engine.ledger.write import literal_include

    content = original
    dest = destinations[path]
    for span in sorted(iter_includes(content), key=lambda item: item.start, reverse=True):
        feed = by_target.get(span.target)
        if feed is not None:
            if (span.target, str(path), span.line) in repeats:
                # The load keeps a feed's first include and ignores repeats.
                # Pointing every one at the same local file made a snapshot
                # stock Beancount refuses as a duplicate filename (w5/100).
                content = _swap_line(content, span.line, f"{_ALREADY_INCLUDED_LINE}\n".encode())
                continue
            replacement = literal_include(os.path.relpath(feed, dest.parent))
            content = content[: span.start] + replacement.encode() + content[span.end :]
            continue
        matches = patterns.get(str(path.parent / span.target), ())
        if matches:
            replacement = "\ninclude ".join(
                literal_include(os.path.relpath(destinations[p], dest.parent)) for p in matches
            )
            content = content[: span.start] + replacement.encode() + content[span.end :]
    return content


def _export_feed_text(source: ManagedSource, at: float) -> str:
    """A marker directive the next stage replays, plus the effective text."""
    if source.revision is None:
        day = datetime.fromtimestamp(at, UTC).strftime("%Y-%m-%d")
        marker = f'{day} custom "bea-managed-source" "{source.alias}" "{source.url}" "none" "unknown" "unknown" 0\n'
        cause = source.error or _NO_CACHED_REVISION
        return f"; bea-managed-error: {cause}\n{marker}"
    effective = source.effective_text or ""
    day = max(source.effective_dates) if source.effective_dates else _iso_day(source.fetched_at, at)
    marker = (
        f'{day} custom "bea-managed-source" "{source.alias}" "{source.url}" '
        f'"{source.revision}" "{source.observed_at or "unknown"}" "{source.fetched_at or "unknown"}" '
        f"{source.shadowed_count}\n"
    )
    return f"{marker}{effective}" if effective.endswith("\n") or not effective else f"{marker}{effective}\n"


def _iso_day(stamp: str | None, at: float) -> str:
    if stamp:
        return stamp[:10]
    return datetime.fromtimestamp(at, UTC).strftime("%Y-%m-%d")


__all__ = [
    "EffectiveFeed",
    "IncludeRef",
    "LoadedLedger",
    "ManagedSource",
    "OFFLINE_ENV",
    "ORIGINS_ENV",
    "PortableExport",
    "STRICT_ENV",
    "apply_ledger_price_precedence",
    "collect_ledger_price_pairs",
    "export_portable",
    "load_file",
    "load_with_sources",
]
