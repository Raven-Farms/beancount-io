"""`python -m bea_engine`, which is how the frontend launches the helper.

The frontend spawns the module rather than the `bea-engine` console script so a
managed environment works whether or not its `bin/` is on `PATH`, and so a
checkout works without installing the engine distribution at all.
"""

from __future__ import annotations

import signal
import sys

try:
    # Typer 0.27 vendors Click; older supported engine environments use the
    # standalone package. Catch the exception class its parser actually uses.
    from typer._click.exceptions import Abort, ClickException
except ImportError:
    from click import Abort, ClickException  # type: ignore[assignment]  # Equivalent parser API before vendoring.

from bea_engine import protocol, stopping
from bea_engine.main import app

# Unwind staged files and locks before reporting the shell's signal status.
_previous_handlers = stopping.install()
try:
    # Let the outer parser raise its own argument errors so they get the
    # same trustworthy envelope as command failures. A missing envelope is
    # still an unknown write outcome: user code can itself invoke Click and
    # exit 2 after changing a file, with identical-looking stderr.
    raise SystemExit(app(standalone_mode=False))
except ClickException as exc:
    with protocol.answering("usage"):
        raise protocol.UsageError(exc.format_message()) from None
except Abort:
    print("Aborted!", file=sys.stderr)
    raise SystemExit(1) from None
finally:
    # The answer is out, or the run is already ending by its own status: a
    # stop from here on is ignored. Restoring the default disposition left
    # tens of milliseconds of interpreter shutdown in which a forwarded stop
    # killed an engine that had answered, and the frontend took the write
    # for uncommitted and died silently (w5/825).
    for number in _previous_handlers:
        signal.signal(number, signal.SIG_IGN)
