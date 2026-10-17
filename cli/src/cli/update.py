"""Telling a person — never a script — that a newer `bea` has been published.

The rules are the ones the sibling bex CLI settled on, and every one of them
exists to keep this out of the way of automation: the notice needs a terminal,
it is silent under `--json`, `--no-input` and `CI`, `BEA_NO_UPDATE_NOTIFIER`
turns it off outright, the index is asked at most once a day, and *any* failure
prints nothing at all. A CI job must never be interrupted, slowed, or failed by
a courtesy message.

Nothing here rewrites an installed file. The notice points at `bea upgrade`,
which hands the work to whichever package manager owns the install.
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from collections.abc import Sequence
from pathlib import Path

from cli.config import cache_dir, config_dir, package_version
from cli.context import env_flag
from cli.errors import BeaError, UsageError

PROJECT = "beancount-io"

#: Where releases are announced. `BEA_UPDATE_API_URL` repoints it at a fake in tests.
DEFAULT_INDEX_URL = "https://pypi.org"
INDEX_URL_ENV = "BEA_UPDATE_API_URL"
TAP_URL = "https://raw.githubusercontent.com/bex-co/homebrew-tap/main/Formula/bea.rb"
TAP_URL_ENV = "BEA_TAP_FORMULA_URL"
DISABLE_ENV = "BEA_NO_UPDATE_NOTIFIER"

#: One check a day, whatever the outcome was.
CACHE_MAX_AGE_SECONDS = 24 * 60 * 60

#: The whole budget for the check: the socket timeout, and the longest a
#: command will wait for the answer before giving up and printing nothing.
TIMEOUT_SECONDS = 3.0


def _cache_name(channel: str) -> str:
    return "update-check-homebrew.json" if channel == "homebrew" else "update-check.json"


def cache_path(channel: str = "pypi") -> Path:
    return config_dir() / _cache_name(channel)


def release_parts(version: str) -> tuple[int, int, int] | None:
    """A canonical `X.Y.Z` release, or `None` for anything else.

    The release channel only ever publishes canonical semver — `release-check.sh`
    refuses to build a tag that is not — so anything else is something this
    module cannot reason about: `0+unknown` from a package with no metadata, a
    checkout's `.dev` version, a local version segment, a pre-release. Those
    stay silent rather than guess. Install-channel gating separately silences
    checkouts even when they carry a canonical release version.
    """
    parts = version.split(".")
    if len(parts) != 3 or not all(p.isascii() and p.isdigit() for p in parts):
        return None
    major, minor, patch = (int(p) for p in parts)
    return major, minor, patch


def is_release(version: str) -> bool:
    return release_parts(version) is not None


def newer(current: str, latest: str) -> bool:
    """Whether `latest` is strictly newer. Anything unreadable is never newer."""
    here, there = release_parts(current), release_parts(latest)
    return here is not None and there is not None and there > here


def hint(current: str, latest: str) -> str:
    """The one line both the passive notice and `bea --version` print, so they cannot drift."""
    return f"bea {latest} is available (you have {current}) — run 'bea upgrade' to update."


def _stderr_is_a_terminal() -> bool:
    """Whether a person is reading. A redirected or closed stderr counts as nobody."""
    try:
        return sys.stderr.isatty()
    except (AttributeError, ValueError):
        return False


def muted(*, json_output: bool, no_input: bool, channel: str = "pypi") -> bool:
    """Every reason to stay quiet that costs nothing to check.

    Deliberately cheap and checked first: resolving the installed version and
    starting a thread are work that a scripted run should never pay for.

    `checkout` and `unknown` are the channels whose `bea upgrade` runs nothing,
    so a notice pointing at it would be advice the user cannot take. They are
    named as strings because `cli.commands.upgrade`, which owns the `Channel`
    values, imports this module.
    """
    return (
        channel in {"checkout", "unknown"}
        or json_output
        or no_input
        or env_flag(DISABLE_ENV)
        or env_flag("CI")
        or not _stderr_is_a_terminal()
    )


def read_cache(channel: str = "pypi", *, cache_file: Path | None = None) -> tuple[float, str] | None:
    """The last check: when it happened, and what it found (`""` for nothing)."""
    try:
        entry = json.loads((cache_file or cache_path(channel)).read_text())
        return float(entry["checked_at"]), str(entry["version"])
    except (OSError, ValueError, KeyError, TypeError, UsageError):
        # UsageError: a refused `BEA_CONFIG_DIR` must not fail `bea --version`.
        return None


def _writable_cache(channel: str) -> Path | None:
    """Where this check's outcome can be remembered: the config directory, else the cache directory.

    A config directory left root-owned by `sudo bea`, or a read-only home,
    turned "at most once a day" into once per command, since nothing ever
    recorded the outcome (w5/321). None when neither place takes a write.
    """
    candidates = [cache_dir() / _cache_name(channel)]
    try:
        candidates.insert(0, cache_path(channel))
    except UsageError:  # A refused `BEA_CONFIG_DIR`: the cache directory still serves.
        pass
    return next((path.absolute() for path in candidates if _can_write(path.absolute())), None)


def _can_write(path: Path) -> bool:
    if path.exists():
        return path.is_file() and os.access(path, os.W_OK)
    holder = next((parent for parent in path.parents if parent.exists()), None)
    return holder is not None and holder.is_dir() and os.access(holder, os.W_OK | os.X_OK)


def write_cache(checked_at: float, version: str, channel: str = "pypi", *, cache_file: Path | None = None) -> None:
    """Remember the outcome. Best effort: a read-only home must not break a command."""
    try:
        path = cache_file or cache_path(channel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"checked_at": checked_at, "version": version}))
    except OSError:
        pass


def _index_url(channel: str) -> str:
    base = os.environ.get(INDEX_URL_ENV) or DEFAULT_INDEX_URL
    if channel == "homebrew":
        return os.environ.get(TAP_URL_ENV) or TAP_URL
    return f"{base.rstrip('/')}/pypi/{PROJECT}/json"


def check_latest(channel: str = "pypi") -> str | None:
    """`bea upgrade --check`'s answer: a fresh fetch whose failure is reported, not swallowed.

    `latest_version` turns every failure into "nothing to report" for the
    silent notice; the explicit check printed `Latest release: unknown` with
    exit 0, so a failed check read as a successful one (w5/322). Only an
    answer is cached here.
    """
    from urllib.error import URLError
    from urllib.parse import urlparse

    try:
        version = _fetch_within_budget(channel)
    except Exception as exc:
        reason = exc.reason if isinstance(exc, URLError) else exc
        host = urlparse(_index_url(channel)).netloc or _index_url(channel)
        raise BeaError(f"Could not check {host} for a newer release: {str(reason) or type(exc).__name__}.") from exc
    write_cache(time.time(), version, channel)
    return version or None


def _fetch_within_budget(channel: str) -> str:
    """`_fetch_latest`, given up on once `TIMEOUT_SECONDS` have passed in all.

    The socket timeout bounds each read, not the request, so an index that
    trickles its answer kept `upgrade --check` waiting half a minute (w5/375).
    The fetch runs on a daemon thread that the deadline abandons; its own read
    loop stops soon after.
    """
    outcome: list[str | BaseException] = []

    def fetch() -> None:
        try:
            outcome.append(_fetch_latest(channel))
        except Exception as exc:
            outcome.append(exc)

    worker = threading.Thread(target=fetch, name="bea-update-fetch", daemon=True)
    worker.start()
    worker.join(TIMEOUT_SECONDS)
    if not outcome:
        raise TimeoutError(f"no answer within {TIMEOUT_SECONDS:g} s")
    if isinstance(outcome[0], BaseException):
        raise outcome[0]
    return outcome[0]


def _fetch_latest(channel: str) -> str:
    """Ask the index for the newest published version. Raises on any failure."""
    # Imported here so that `bea --help` never loads urllib, and so nothing in
    # this module pulls in an HTTP client the default install would rather skip.
    import urllib.request

    request = urllib.request.Request(
        _index_url(channel),
        headers={"Accept": "application/json", "User-Agent": f"bea/{package_version()}"},
    )
    deadline = time.monotonic() + TIMEOUT_SECONDS
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        # Whatever has arrived, chunk by chunk, against one deadline for the
        # whole body: `read()` would wait out a trickle byte by byte (w5/375).
        chunks: list[bytes] = []
        while chunk := response.read1(65536):
            chunks.append(chunk)
            if time.monotonic() > deadline:
                raise TimeoutError(f"no complete answer within {TIMEOUT_SECONDS:g} s")
    body = b"".join(chunks)
    # An HTML page or a JSON shape without `info.version` surfaced as Python's
    # own parser text (`Expecting value: line 1 column 1 (char 0)`, `'version'`)
    # in the check's failure (w5/484).
    try:
        if channel == "homebrew":
            formula = body.decode("utf-8")
            match = re.search(r'^\s*version "(\d+\.\d+\.\d+)"\s*$', formula, re.MULTILINE)
            if not match:
                match = re.search(r"beancount_io-(\d+\.\d+\.\d+)\.tar\.gz", formula)
            return match.group(1) if match else ""
        payload = json.loads(body)
        return str(payload["info"]["version"])
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError("the index sent an unreadable answer") from exc


def latest_version(
    *, use_cache: bool = True, now: float | None = None, channel: str = "pypi", cache_file: Path | None = None
) -> str | None:
    """The newest published release, or `None` when there is nothing to report.

    Every outcome — a version, an empty answer, a failed fetch — is cached for a
    day, so an offline machine pays one timeout per day rather than one per
    command. `use_cache=False` is for the paths where the user explicitly asked
    (`bea upgrade --check`) and deserves a fresh answer.
    """
    cache_file = cache_file or cache_path(channel).absolute()
    checked_at = time.time() if now is None else now
    if use_cache:
        cached = read_cache(channel, cache_file=cache_file)
        if cached is not None and 0 <= checked_at - cached[0] < CACHE_MAX_AGE_SECONDS:
            return cached[1] or None

    try:
        version = _fetch_latest(channel)
    except Exception:
        # A courtesy check has no failure mode worth showing anyone: a bad
        # network, a rate limit, a changed payload all mean "say nothing".
        version = ""
    write_cache(checked_at, version, channel, cache_file=cache_file)
    return version or None


_pending: tuple[str, threading.Thread, list[str | None], str, Path] | None = None


def start(*, json_output: bool, no_input: bool, channel: str = "pypi", offline: bool = False) -> None:
    """Begin the daily check alongside the command, so a person waits for nothing.

    `--offline` means no network at all: a run on a plane or in a sandbox still
    asked the release index and printed its notice (w5/458).
    """
    global _pending
    _pending = None
    if offline or muted(json_output=json_output, no_input=no_input, channel=channel):
        return
    version = package_version()
    if not is_release(version):
        return

    found: list[str | None] = [None]
    # Resolve before starting the worker: a command can finish (or fail)
    # before the fetch does, and an embedding process may restore its env.
    cache_file = _writable_cache(channel)
    if cache_file is None:
        # An outcome that cannot be remembered would be fetched again by
        # every command: offline, each one stalled the full timeout (w5/321).
        return

    def check() -> None:
        found[0] = latest_version(channel=channel, cache_file=cache_file)

    thread = threading.Thread(target=check, name="bea-update-check", daemon=True)
    thread.start()
    _pending = (version, thread, found, channel, cache_file)


def suppress() -> None:
    """Drop a check in flight, for a command that speaks about versions itself.

    `bea upgrade` is the case: after it runs, this process still reports the
    version it started with, so the notice would announce a release the user
    just installed.
    """
    global _pending
    _pending = None


def print_notice() -> None:
    """Print the notice after the command's own output, or print nothing.

    Only a run that missed the day's cache can wait here at all, and it waits no
    longer than the fetch's own timeout: a hung index costs the timeout once a
    day and simply skips the notice. The failure is cached here when the check
    is still running, because the daemon thread dies at exit before it writes
    the cache, and a trickling index otherwise cost every command the timeout,
    every run (w5/375).
    """
    global _pending
    pending, _pending = _pending, None
    if pending is None:
        return
    version, thread, found, channel, cache_file = pending
    thread.join(TIMEOUT_SECONDS)
    if thread.is_alive():
        write_cache(time.time(), "", channel, cache_file=cache_file)
        return
    latest = found[0]
    if latest is not None and newer(version, latest):
        print(hint(version, latest), file=sys.stderr)


def print_version_hint(version: str, argv: Sequence[str], *, channel: str = "pypi") -> None:
    """The hint `bea --version` may add — from the day's cache, never from the network.

    `--version` is an eager flag: it answers before the root callback has built
    the run context, so the two machine-mode flags are read from `argv` here
    instead. The hint goes to stderr so that stdout stays exactly one parseable
    `bea X.Y.Z` line.
    """
    if muted(json_output="--json" in argv, no_input="--no-input" in argv, channel=channel):
        return
    # Whatever the last check found, however old: a stale answer here can only
    # be wrong in the harmless direction, because once the user has upgraded
    # `newer()` stops reporting it.
    cached = read_cache(channel)
    latest = cached[1] if cached is not None else ""
    if latest and newer(version, latest):
        print(hint(version, latest), file=sys.stderr)
