"""The `bea` console script: Ctrl-C at any point is the documented silent exit 130.

`cli.main` turns an interrupt into exit 130 once the root group invokes a
command. Before that, Python imports the command modules and Typer builds
the command tree, which together take most of a warm start (about 70 ms) and
longer on a cold one. A Ctrl-C landing there reached the interpreter's default
handler, which printed a coloured `KeyboardInterrupt` traceback and died of
SIGINT (w5/342). This wrapper owns that window; it imports nothing heavy
itself, so startup time is unchanged.
"""

from __future__ import annotations

import sys


def main() -> None:
    import os

    if "_BEA_COMPLETE" in os.environ:
        # Typer renders each fish candidate's help through Rich at the terminal
        # width, and a completion process has no terminal: help wrapped onto
        # lines without a tab, which fish offered as candidates (w5/421).
        os.environ["TERMINAL_WIDTH"] = "100000"
    try:
        from cli.main import app

        app()
    except KeyboardInterrupt:
        sys.exit(130)
