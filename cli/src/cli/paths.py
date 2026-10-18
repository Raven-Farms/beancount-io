"""User-supplied filesystem paths, checked before a command uses them."""

from pathlib import Path

from cli.errors import UsageError


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
