"""Amount-string validation shared by structured input and CSV extraction."""

from __future__ import annotations

import math
import re
from decimal import Decimal, Inexact, Rounded, localcontext
from typing import Any

_PLAIN_DECIMAL = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)")
"""A decimal without exponent notation, the only spelling that reaches here."""

_QUOTED_OR_COMMENT = re.compile(r'"(?:[^"\\]|\\.)*"|;[^\r\n]*')
"""Quoted strings and comments, inside which an `@@` is text, not a price."""


def parse_decimal_number(value: str, *, grouping: bool = True) -> Decimal:
    """The frontend's finite ASCII decimal rule, repeated across the engine boundary.

    Comma grouping in threes (`1,538.25`) is the flag spelling Beancount's own
    grammar reads; a structured field passes `grouping=False`, because its
    text is converted as written rather than through this result.
    """
    text = value.strip()
    require_decimal_notation(text)
    if grouping and re.fullmatch(r"[+-]?[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]*)?", text):
        return Decimal(text.replace(",", ""))
    if not re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)", text):
        if grouping and "," in text:
            raise ValueError(
                f"Invalid amount {value!r}. A comma is read only as a thousands separator between groups of "
                "three digits, such as '1,538.25'; write the fraction after a decimal point, or remove the separators."
            )
        raise ValueError(f"Invalid amount {value!r}. Use finite decimal notation with ASCII digits, such as '1538.25'.")
    return Decimal(text)


def require_plain_decimal(value: Any) -> Any:
    """`require_decimal_notation`, plus `parse_decimal_number`'s ASCII rule for text.

    `Decimal()` also reads `1_000`, Arabic-Indic and full-width digits, which
    Beancount's own grammar — and so `add transaction --posting` — refuses.
    Already-converted Decimals and integers pass unchanged.
    """
    require_decimal_notation(value)
    if isinstance(value, str):
        parse_decimal_number(value, grouping=False)
    return value


def parse_exact(text: str) -> tuple[list[Any], list[Any], dict[str, Any]]:
    """Beancount's `parser.parse_string`, with every typed number kept digit for digit.

    The grammar evaluates a leading minus as arithmetic under the active
    decimal context, so `-12345678901.123456789012345678` came back rounded to
    28 significant digits while its positive twin was read exactly, and the
    rounded figure was what `bea` then wrote (w5/263). A parse that rounded is
    repeated under a context wide enough for any number the text can spell.
    Only a quotient that does not terminate (`1/3`) fills that precision, and
    it keeps Beancount's own 28-digit reading.
    """
    from beancount.parser import parser as beancount_parser

    with localcontext() as narrow:
        narrow.clear_flags()
        parsed: tuple[list[Any], list[Any], dict[str, Any]] = beancount_parser.parse_string(text)
        if not narrow.flags[Rounded]:
            return parsed
    with localcontext() as wide:
        # No literal, sum or product in the text has more digits than the text has characters.
        wide.prec = max(wide.prec, len(text)) + 2
        wide.clear_flags()
        exact: tuple[list[Any], list[Any], dict[str, Any]] = beancount_parser.parse_string(text)
        if not wide.flags[Inexact]:
            return exact
        return _typed_digits(parsed[0], exact[0], wide.prec), parsed[1], parsed[2]


def _typed_digits(rounded: Any, exact: Any, precision: int) -> Any:
    """`rounded`, with each number the wider parse read exactly taken from `exact`."""
    if isinstance(exact, Decimal):
        return rounded if len(exact.as_tuple().digits) >= precision else exact
    if isinstance(exact, list) and isinstance(rounded, list) and len(exact) == len(rounded):
        return [_typed_digits(*pair, precision) for pair in zip(rounded, exact, strict=True)]
    if isinstance(exact, tuple) and hasattr(exact, "_fields") and type(exact) is type(rounded):
        return type(exact)(*(_typed_digits(*pair, precision) for pair in zip(rounded, exact, strict=True)))
    return rounded


def split_total_price(text: str) -> tuple[str, str] | None:
    """The `@@` total from a posting line as `(number, currency)` strings, or None.

    The caller has already validated the line through Beancount's parser, so
    a total that cannot be read here means the split misread the text — never
    a user error — and the caller falls back to the parsed unit price. A total
    written as native arithmetic (`@@ (40+60) USD`, `@@ 200/2 USD`) is
    evaluated by that same parser rather than here: the fallback would
    otherwise record it as a divided, repeating `@` price.
    """
    unquoted = _QUOTED_OR_COMMENT.sub("", text)
    if "@@" not in unquoted:
        return None
    tail = unquoted.rsplit("@@", 1)[1].split()
    if len(tail) < 2:
        return None
    if len(tail) == 2 and _PLAIN_DECIMAL.fullmatch(tail[0]):
        return tail[0], tail[1]
    return _evaluated_amount(" ".join(tail[:-1]), tail[-1])


def _evaluated_amount(expression: str, currency: str) -> tuple[str, str] | None:
    """A native arithmetic amount as Beancount evaluates it, or None when it does not parse as one."""
    from beancount.core.number import MISSING
    from beancount.parser import parser as beancount_parser

    entries, errors, _ = beancount_parser.parse_string(
        f'2026-01-02 * "probe"\n  Assets:Probe {expression} {currency}\n  Equity:Probe\n'
    )
    entry: Any = entries[0] if len(entries) == 1 and not errors else None
    if entry is None or len(entry.postings) != 2:
        return None
    posting: Any = entry.postings[0]
    units: Any = posting.units
    if posting.cost is not None or posting.price is not None or units is None or units is MISSING:
        return None
    if units.number is MISSING or units.currency != currency:
        return None
    return format(units.number, "f"), currency


def refuse_zero_divisor(text: str) -> None:
    """Refuse a literal zero divisor, which crashes Beancount's parser instead of erroring.

    The frontend's `check_decimal_notation` makes the same check for flag
    input; a bulk row's amount fragment reaches the engine without passing
    it. Quoted labels and comments are text, and anything computed
    (`100/(2-2)`) is still upstream's to answer.
    """
    if re.search(r"/\s*[-+]?(?:0+(?:\.0*)?|\.0+)(?![\d.A-Z'_-])", _QUOTED_OR_COMMENT.sub("", text)):
        raise ValueError(
            f"Division by zero in {text.strip()!r}. Beancount evaluates amount arithmetic while parsing, "
            "and a zero divisor crashes it outright, so bea refuses the expression instead of sending it."
        )


def decimal_string_hint(value: float, noun: str) -> str:
    """What to send instead of a JSON float: a string this same input accepts.

    `str()` of a float is scientific for large or tiny values (`1e+20`,
    `1e-08`) and `nan`/`inf` for the rest, each refused on the next run; an
    agent following the hint looped between two errors (w5/335).
    """
    if not math.isfinite(value):
        return f"{value!r} is not a finite number, so it has no decimal form."
    return f"Send the {noun} as a decimal string, such as '{format(Decimal(repr(value)), 'f')}'."


def require_decimal_notation(value: Any) -> Any:
    """Reject exponent notation and JSON floats before conversion; internal Decimals remain valid.

    A float is refused even when it prints cleanly: the double is already the
    wrong value (0.1 + 0.2 arrives as 0.30000000000000004), so accepting it
    would record binary error as accounting fact. Integers are exact and stay.
    """
    if isinstance(value, float):
        raise ValueError(
            f"JSON number {value!r} is not supported in Beancount amounts; "
            f"floats cannot represent decimals exactly. {decimal_string_hint(value, 'amount')}"
        )
    if isinstance(value, str) and re.fullmatch(
        r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)[eE][+-]?\d+", value.strip().replace("_", "")
    ):
        raise ValueError(
            f"Scientific notation {value!r} is not supported in Beancount amounts. "
            "Use decimal notation, such as '1000' instead of '1e3'."
        )
    return value
