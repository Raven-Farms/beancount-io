"""Pinned upstream interfaces, available without provisioning or frontend imports."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path


@cache
def _commands() -> dict[str, str]:
    data = json.loads((Path(__file__).parent / "engine/native-help.json").read_text())
    return dict(data["commands"])


#: Options bea reads out of the forwarded arguments itself. They are not
#: declared parameters, so this text is the only place help and the generated
#: reference can list them; keep it in step with the command's own parsing.
_BEA_OPTIONS = {
    "price": (
        "bea options (bea price export; read by bea, not forwarded):\n\n\b\n"
        "  -o, --output DIR  Export into DIR (default: <ledger>-export/ beside the ledger).\n"
        "  --allow-errors    Export even when a managed source is unavailable.\n"
        "  --force           Overwrite files already at the paths the export writes."
    ),
    "example": ("bea options (read by bea, not forwarded):\n\n\b\n  --force  Overwrite an existing -o/--output file."),
    "treeify": (
        "bea options (read by bea, not forwarded):\n\n\b\n"
        "  --force  Overwrite an existing .bean/.beancount file named by -o/--output."
    ),
}


def native_help(command: str) -> str:
    """Append upstream usage verbatim while keeping bea's own options above it."""
    note = "Native interface (arguments/options are forwarded by bea):"
    if command == "check":
        note = "Native interface: FILENAME comes from bea --file; use global --json for bea's JSON envelope."
    own = _BEA_OPTIONS.get(command)
    if own is not None:
        note = own + "\n\n" + note
    return note + "\n\n\b\n" + _commands()[command].replace("\n\n", "\n\n\b\n")
