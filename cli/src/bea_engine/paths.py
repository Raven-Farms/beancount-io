"""User-supplied filesystem paths, checked before a helper operation uses them."""

from pathlib import Path

from bea_engine.protocol import UsageError


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
