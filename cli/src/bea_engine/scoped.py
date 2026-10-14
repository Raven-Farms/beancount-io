"""`doctor region` / `doctor linked`, numbered from the amounts actually in scope.

Upstream builds the balance tree's number format from the *whole* ledger's
display context, whose precision is the most common one it saw. A region holding
`5.50 USD` therefore prints `6 USD` in a book whose other amounts are whole
numbers — while the `Net Income` line directly below it, which does not go
through that format, still says `-5.50 USD`. One balance, two numbers, one
screen.

Upstream keeps every decision here: which entries the argument selects — link,
tag, location or region — the realization, the conversion, the rendering and the
exit status. All bea supplies is the display context, built from the entries
upstream itself chose, so the tree is numbered like the postings it is a tree of.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


def run(op: str, argv: list[str]) -> int:
    """Run `bean-doctor <op>` in this process, formatting balances in scope."""
    from beancount.scripts import doctor

    from bea_engine.ledger.write import keep_load_cache_private

    keep_load_cache_private()
    upstream: Any = doctor
    plain_loader = upstream.loader
    upstream.loader = _ManagedLoader(plain_loader)
    try:
        original = getattr(upstream, "render_mini_balances", None)
        if original is None:  # pragma: no cover - upstream renamed it; run unchanged
            return _invoke(upstream, op, argv)

        def in_scope(entries: Any, options_map: Any, conversion: Any = None, price_map: Any = None) -> Any:
            scoped = {**options_map, "dcontext": _context_of(entries, options_map)}
            return original(entries, scoped, conversion, price_map)

        upstream.render_mini_balances = in_scope
        try:
            return _invoke(upstream, op, argv)
        finally:
            upstream.render_mini_balances = original
    finally:
        upstream.loader = plain_loader


class _ManagedLoader:
    """`beancount.loader` as upstream's doctor uses it, with managed price includes resolved.

    Upstream loads the ledger itself, and its loader reads a managed include
    as a file glob that matches nothing: `region --conversion value` left a
    holding `balance` valued at market unvalued, and `roundtrip` congratulated
    over the glob error (w5/286). A ledger naming a managed source loads the
    way every other command loads it; any other keeps upstream's own load.
    """

    def __init__(self, plain: Any) -> None:
        self._plain = plain

    def __getattr__(self, name: str) -> Any:
        return getattr(self._plain, name)

    def load_file(self, filename: Any, *args: Any, **kwargs: Any) -> Any:
        from bea_engine import managed_load

        entry = Path(filename)
        if not managed_load.names_managed_source(entry):
            return self._plain.load_file(filename, *args, **kwargs)
        loaded = managed_load.load_with_sources(entry)
        return loaded.entries, loaded.errors, loaded.options


def _invoke(upstream: Any, op: str, argv: list[str]) -> int:
    """Upstream's own command line, so its usage errors and status are its own."""
    from bea_engine import protocol

    try:
        upstream.doctor.main(args=[op, *argv], prog_name="bean-doctor")
    except SystemExit as exit_status:
        return _status(exit_status.code)
    except protocol.EngineError as exc:
        # Only the managed load raises one: strict prices, or a directory it cannot stage in.
        protocol.note(f"error: {exc}")
        return exc.exit_code
    return 0


def _status(code: object) -> int:
    """What CPython itself would do with this `SystemExit` code.

    `SystemExit.code` is not always int-or-None: `bean-doctor linked` validates
    the location itself and raises `SystemExit("Invalid line number or link
    format for location.")` — a *string* code, which CPython prints to stderr
    before exiting 1. Running upstream in-process instead of as a child put
    that string through `int()`, and the `ValueError` reached the engine's rich
    traceback handler: 118 lines of bea internals in place of upstream's one
    sentence. Reproducing CPython's rule here is exactly the passthrough the
    docstring above promises.
    """
    if code is None:
        return 0
    if isinstance(code, int):
        return code
    print(code, file=sys.stderr)
    return 1


def _context_of(entries: Any, options_map: Any) -> Any:
    """A display context holding only these entries' amounts.

    Falls back to the ledger's own context when the scope carries no amount to
    learn from, so an empty selection renders exactly as it did before.
    """
    from beancount.core import data, display_context

    class _ExactInScope(display_context.DisplayContext):
        """Formats at each currency's finest in-scope precision.

        Upstream renders the tree with this context's default `build()`, which
        picks the *most common* precision. With two whole-number postings and
        one in cents, the tree dropped the cents and disagreed with the
        `Net Income` line beneath it: `Checking 1755 USD` over
        `Net Income: (1754.75 USD)` (w5/101). No scoped amount is rounded.
        """

        def build(self, *args: Any, **kwargs: Any) -> Any:
            kwargs["precision"] = display_context.Precision.MAXIMUM
            return super().build(*args, **kwargs)

    context = _ExactInScope()
    seen = False
    for entry in data.filter_txns(entries):
        for posting in entry.postings:
            if posting.units is not None and posting.units.number is not None:
                context.update(posting.units.number, posting.units.currency)
                seen = True
    if not seen:
        return options_map["dcontext"]
    ledger_context = options_map.get("dcontext")
    if ledger_context is not None:
        context.set_commas(ledger_context.commas)
    return context
