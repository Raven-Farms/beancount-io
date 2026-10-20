"""User-supplied filesystem paths, checked before a helper operation uses them."""

import re
from pathlib import Path

from bea_engine.protocol import UsageError

#: Twin of `cli.paths._DESCRIPTOR`: the two execution environments cannot
#: import each other (w5/792).
_DESCRIPTOR = re.compile(r"/dev/stdin|/dev/fd/(\d+)|/proc/self/fd/(\d+)")


def is_descriptor_path(path: Path | str) -> bool:
    """Whether the path spells a file descriptor rather than a file."""
    return _DESCRIPTOR.fullmatch(str(path)) is not None


def expand_path(path: Path, source: str) -> Path:
    """Expand a home directory, reporting an unresolved home as bad input.

    Keep this twin of `cli.paths.expand_path` independent of the frontend:
    the two execution environments cannot import each other.
    """
    try:
        return path.expanduser()
    except RuntimeError:
        raise UsageError(
            f"Cannot expand {source} path {str(path)!r}: could not determine home directory. "
            "Use ~/, a valid ~user, or an explicit path."
        ) from None
