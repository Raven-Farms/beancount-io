"""User-supplied filesystem paths, checked before a command uses them."""

import errno
import os
import re
from pathlib import Path

from cli.errors import UsageError

#: Spellings that name one of this process's file descriptors rather than a
#: file: what `<(…)` passes, what a `< file` or `N< file` redirect leaves
#: behind `/dev/stdin` and `/dev/fd/N`, and the Linux spelling (w5/792).
_DESCRIPTOR = re.compile(r"/dev/stdin|/dev/fd/(\d+)|/proc/self/fd/(\d+)")


def descriptor_number(path: Path | str) -> int | None:
    """The descriptor a descriptor spelling names, or None for a real path."""
    match = _DESCRIPTOR.fullmatch(str(path))
    if match is None:
        return None
    return int(match.group(1) or match.group(2) or 0)


def is_descriptor_path(path: Path | str) -> bool:
    """Whether the path spells a file descriptor rather than a file."""
    return descriptor_number(path) is not None


def held_descriptor(path: Path | str) -> int | None:
    """The descriptor a spelling names when this process holds it open."""
    number = descriptor_number(path)
    if number is None:
        return None
    try:
        os.fstat(number)
    except OSError:
        return None
    return number


def refuse_too_long_name(path: Path | str, named: str) -> None:
    """Refuse a path the filesystem will not look up because a name in it is too long.

    Since Python 3.12 `Path.exists()` raises ENAMETOOLONG instead of answering
    False, so a 256-byte name given to `-f`, `-o` or `--into` died on a raw
    `[Errno 63] File name too long`, exit 1 (w5/817). `named` says which
    flag, or which source, supplied it.
    """
    try:
        os.lstat(path)
    except OSError as exc:
        if exc.errno == errno.ENAMETOOLONG:
            raise UsageError(f"{named} {path} has a name too long for the filesystem; choose a shorter one.") from None


def expand_path(path: Path, source: str) -> Path:
    """Expand a home directory, reporting an unresolved home as bad input.

    Keep this twin of `bea_engine.paths.expand_path` independent of the
    engine: the two execution environments cannot import each other.
    """
    try:
        return path.expanduser()
    except RuntimeError:
        raise UsageError(
            f"Cannot expand {source} path {str(path)!r}: could not determine home directory. "
            "Use ~/, a valid ~user, or an explicit path."
        ) from None
