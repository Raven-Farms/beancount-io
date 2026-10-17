"""Refuse two different values for one single-valued option.

Click keeps the last value of a repeated scalar option, so `-a One -a Two`
or an alias pair such as `--commodity HOOL --currency USD` would act on one
value and report success while dropping the other. `add` refused that
(w5/238); `import` booked rows to the second `--account` and remembered it,
and `init -c USD -c EUR` wrote EUR alone (w5/311).
"""

from __future__ import annotations

from typing import Any

from typer._click.parser import _OptionParser
from typer.core import TyperCommand

from cli.errors import UsageError


class _SingleValueParser(_OptionParser):
    def __init__(self, ctx: Any = None, *, advice: str) -> None:
        super().__init__(ctx)
        self._given: dict[str, tuple[str, Any]] = {}
        self._advice = advice

    def _get_value_from_state(self, option_name: str, option: Any, state: Any) -> Any:
        value = super()._get_value_from_state(option_name, option, state)
        if option.action != "store" or option.dest is None:
            return value
        earlier_name, earlier = self._given.setdefault(option.dest, (option_name, value))
        if earlier != value:
            command = self.ctx.command.name if self.ctx is not None else None
            hint = (
                " Both name the commodity being priced; the quote currency belongs in --amount."
                if command == "price" and option.dest == "currency"
                else ""
            )
            raise UsageError(
                f"Conflicting values for one option: {earlier_name} {earlier!r} and {option_name} {value!r}. "
                f"{self._advice}{hint}"
            )
        return value


def single_value_parser(command: Any, ctx: Any, advice: str = "Pass it once.") -> _OptionParser:
    """`command`'s option parser, refusing a second, different value for any scalar option.

    The root group uses it too: `bea -f main.bean -f other.bean add …` wrote to
    `other.bean` with exit 0 (w5/485).
    """
    parser = _SingleValueParser(ctx, advice=advice)
    for param in command.get_params(ctx):
        param.add_to_parser(parser, ctx)
    return parser


class SingleValueCommand(TyperCommand):
    """A command whose scalar options may repeat only with the same value."""

    advice = "Pass it once."

    def make_parser(self, ctx: Any) -> _OptionParser:
        return single_value_parser(self, ctx, self.advice)
