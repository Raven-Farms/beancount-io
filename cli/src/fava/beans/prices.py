"""Price helpers."""

from __future__ import annotations

import datetime
from bisect import bisect
from collections import Counter, defaultdict
from decimal import Decimal
from typing import TYPE_CHECKING


if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable, Sequence

    from .abc import Price

    type BaseQuote = tuple[str, str]
    type PricePoint = tuple[datetime.date, Decimal]

ZERO = Decimal()
ONE = Decimal(1)


class DateKeyWrapper(list[datetime.date]):
    """A class wrapping a list of prices for bisect.

    This is needed before Python 3.10, which adds the key argument.
    """

    __slots__ = ("inner",)

    def __init__(self, inner: list[PricePoint]) -> None:
        self.inner = inner

    def __len__(self) -> int:
        return len(self.inner)

    def __getitem__(self, k: int) -> datetime.date:  # type: ignore[override]
        return self.inner[k][0]


def _keep_last_per_day(
    prices: Sequence[PricePoint],
) -> Iterable[PricePoint]:
    """In a sorted non-empty list of prices, keep the last one for each day.

    Yields:
        The filtered prices.
    """
    prices_iter = iter(prices)
    last = next(prices_iter)
    for price in prices_iter:
        if price[0] > last[0]:
            yield last
        last = price
    yield last


class FavaPriceMap:
    """A Fava alternative to Beancount's PriceMap.

    By having some more methods on this class, fewer helper functions need to
    be imported. Also, this is fully typed and allows to more easily reproduce
    issues with the whole price logic.

    This behaves slightly differently than Beancount. Beancount creates a list
    for each currency pair and then merges the inverse rates. We just create
    both the lists in tandem and count the directions that prices occur in.

    Args:
        price_entries: A sorted list of price entries.
        operating_currencies: The ledger's operating currencies, in option
            order; ``at_value`` values cost-less holdings into these.
    """

    def __init__(
        self,
        price_entries: Iterable[Price],
        operating_currencies: Sequence[str] = (),
    ) -> None:
        self.operating_currencies = tuple(operating_currencies)
        direct: dict[BaseQuote, list[PricePoint]] = defaultdict(list)
        counts: Counter[BaseQuote] = Counter()

        for price in price_entries:
            base_quote = (price.currency, price.amount.currency)
            direct[base_quote].append((price.date, price.amount.number))
            counts[base_quote] += 1
        self._forward_pairs = [(base, quote) for (base, quote), count in counts.items() if counts.get((quote, base), 0) < count]
        # Beancount.io change: settle a pair quoted in both directions the way
        # Beancount's `build_price_map` does, so a same-day reciprocal pair
        # values a holding as BQL does, whatever the line order. Fava appended
        # each rate and its inverse in entry order and kept the last of the
        # day, so `balance` and `bean-query` disagreed (w5/556). The direction
        # quoted fewer times (on a tie, the one seen second) is inverted and
        # appended after the other's own rates, so on a shared day it wins.
        settled: dict[BaseQuote, list[PricePoint]] = {}
        for (base, quote), rates in direct.items():
            if (base, quote) in settled or (quote, base) in settled:
                continue
            reverse = direct.get((quote, base), [])
            keep, drop = ((quote, base), rates) if len(rates) < len(reverse) else ((base, quote), reverse)
            settled[keep] = direct[keep] + [(date, ONE / rate) for date, rate in drop if rate != ZERO]
        self._map: dict[BaseQuote, list[PricePoint]] = {}
        for (base, quote), rates in settled.items():
            kept = list(_keep_last_per_day(sorted(rates, key=lambda point: point[0])))
            self._map[base, quote] = kept
            inverse = [(date, ONE / rate) for date, rate in kept if rate != ZERO]
            if inverse:
                self._map[quote, base] = inverse

    def commodity_pairs(
        self,
        operating_currencies: Sequence[str],
    ) -> list[BaseQuote]:
        """List pairs of commodities.

        Args:
            operating_currencies: A list of operating currencies.

        Returns:
            A list of pairs of commodities. Pairs of operating currencies will
            be given in both directions not just in the one most commonly found
            in the file.
        """
        forward_pairs = self._forward_pairs
        extra_operating_pairs = []
        for base, quote in forward_pairs:
            if base in operating_currencies and quote in operating_currencies:
                extra_operating_pairs.append((quote, base))
        return sorted(forward_pairs + extra_operating_pairs)

    def get_all_prices(self, base_quote: BaseQuote) -> list[PricePoint] | None:
        """Get all prices for the given currency pair."""
        return self._map.get(base_quote)

    def get_price(
        self,
        base_quote: BaseQuote,
        date: datetime.date | None = None,
    ) -> Decimal | None:
        """Get the price for the given currency pair."""
        return self.get_price_point(base_quote, date)[1]

    def get_price_point(
        self,
        base_quote: BaseQuote,
        date: datetime.date | None = None,
    ) -> PricePoint | tuple[None, Decimal] | tuple[None, None]:
        """Get the price point for the given currency pair."""
        base, quote = base_quote
        if base == quote:
            return (None, ONE)

        price_list = self._map.get(base_quote)
        if price_list is None:
            return (None, None)

        if date is None:
            return price_list[-1]

        index = bisect(DateKeyWrapper(price_list), date)
        if index == 0:
            return (None, None)
        return price_list[index - 1]
