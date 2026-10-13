"""A generated feed never lands on a copied file that differs only by case (w5/189).

`export_portable` allocated each feed's `prices/<ALIAS>.beancount` against the
copied files by exact path. On a case-insensitive volume — the macOS default —
a ledger's own `prices/btc-usd.beancount` and the `BTC-USD` feed's file are one
file, so the feed text was written over the copy: exit 0, "Exported 3 files",
two on disk, the manual prices gone and the snapshot valued differently from
its source. Planned names are now compared the way such a volume compares
them, on every platform, so the snapshot also survives being moved to one.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

from bea_engine.managed_load import _free_feed_directory, _free_feed_path
from tests.test_price import _FeedHandler, _run_bea
from tests.test_price import feed_server as feed_server
from tests.test_price_export_repeated_feed_include import _stock_check

FEED_PRICE = "112000.00"
LOCAL_PRICES = "2026-01-01 price BTC 90000.00 USD\n2026-10-01 price BTC 170000.00 USD\n"
LOCAL_NUMBERS = {"90000.00", "170000.00"}
VALUE = "SELECT convert(sum(position), 'USD') AS worth WHERE account ~ 'Wallet'"


def _books(tmp_path: Path, feed_server: str, local_name: str, feeds: tuple[str, ...] = ("BTC-USD",)) -> Path:
    books = tmp_path / "books"
    (books / "prices").mkdir(parents=True)
    (books / "main.bean").write_text(
        'option "operating_currency" "USD"\n'
        "2026-01-01 open Assets:Wallet BTC\n"
        "2026-01-01 open Equity:Opening\n"
        '2026-01-02 * "Open"\n'
        "  Assets:Wallet  2 BTC {50000 USD}\n"
        "  Equity:Opening\n"
        + "".join(f'include "{feed_server}/prices/{feed}"\n' for feed in feeds)
        + f'include "prices/{local_name}"\n'
    )
    (books / "prices" / local_name).write_text(LOCAL_PRICES)
    return books / "main.bean"


def _json(tmp_path: Path, feed_server: str, ledger: Path, *args: str) -> object:
    done = _run_bea(tmp_path, feed_server, "--json", "--file", str(ledger), *args)
    assert done.returncode == 0, done.stderr + done.stdout
    return json.loads(done.stdout)["data"]


def _price_numbers(tmp_path: Path, feed_server: str, ledger: Path) -> list[str]:
    rows = _json(tmp_path, feed_server, ledger, "list", "price")
    assert isinstance(rows, list)
    return sorted(str(row["amount"]["number"]) for row in rows)


def _export(tmp_path: Path, feed_server: str, ledger: Path) -> Path:
    out = tmp_path / "out"
    exported = _run_bea(tmp_path, feed_server, "--file", str(ledger), "price", "export", "--output", str(out))
    assert exported.returncode == 0, exported.stderr
    return out


def _names(directory: Path) -> list[str]:
    return sorted(path.name for path in directory.iterdir())


class TestFeedPathAllocation:
    def test_a_name_taken_in_another_case_steps_aside(self) -> None:
        taken = {Path("/x/prices/btc-usd.beancount")}

        assert _free_feed_path(Path("/x/prices"), "BTC-USD", taken) == Path("/x/prices/BTC-USD-managed.beancount")

    def test_the_suffixed_name_is_compared_the_same_way(self) -> None:
        taken = {Path("/x/prices/btc-usd.beancount"), Path("/x/prices/Btc-Usd-Managed.beancount")}

        assert _free_feed_path(Path("/x/prices"), "BTC-USD", taken) == Path("/x/prices/BTC-USD-managed-2.beancount")

    def test_a_name_taken_in_another_unicode_form_steps_aside(self) -> None:
        composed, decomposed = unicodedata.normalize("NFC", "É-USD"), unicodedata.normalize("NFD", "é-usd")
        taken = {Path(f"/x/prices/{decomposed}.beancount")}

        assert _free_feed_path(Path("/x/prices"), composed, taken) == Path(f"/x/prices/{composed}-managed.beancount")

    def test_a_different_name_is_still_free(self) -> None:
        taken = {Path("/x/prices/eth-usd.beancount"), Path("/x/other/btc-usd.beancount")}

        assert _free_feed_path(Path("/x/prices"), "BTC-USD", taken) == Path("/x/prices/BTC-USD.beancount")

    def test_a_copied_file_named_like_the_directory_in_another_case_moves_it(self) -> None:
        """The same comparison for the feed directory (w5/191)."""
        assert _free_feed_directory(Path("/x"), {Path("/x/Prices")}) == Path("/x/prices-managed")
        assert _free_feed_directory(Path("/x"), {Path("/x/prices.bean")}) == Path("/x/prices")


def test_a_local_price_file_named_in_another_case_survives(feed_server: str, tmp_path: Path) -> None:
    ledger = _books(tmp_path, feed_server, "btc-usd.beancount")

    out = _export(tmp_path, feed_server, ledger)

    assert _names(out / "prices") == ["BTC-USD-managed.beancount", "btc-usd.beancount"]
    assert (out / "prices" / "btc-usd.beancount").read_text() == LOCAL_PRICES
    assert FEED_PRICE in (out / "prices" / "BTC-USD-managed.beancount").read_text()
    copied = (out / "main.bean").read_text()
    assert 'include "prices/BTC-USD-managed.beancount"' in copied
    assert 'include "prices/btc-usd.beancount"' in copied


def test_the_snapshot_prices_and_values_like_its_source(feed_server: str, tmp_path: Path) -> None:
    ledger = _books(tmp_path, feed_server, "btc-usd.beancount")

    out = _export(tmp_path, feed_server, ledger)

    assert _stock_check(out / "main.bean").returncode == 0
    prices = _price_numbers(tmp_path, feed_server, out / "main.bean")
    assert prices == _price_numbers(tmp_path, feed_server, ledger)
    assert set(prices) > LOCAL_NUMBERS | {FEED_PRICE}
    source_worth = _json(tmp_path, feed_server, ledger, "query", VALUE)
    assert "340000" in json.dumps(source_worth), source_worth
    assert _json(tmp_path, feed_server, out / "main.bean", "query", VALUE) == source_worth


def test_the_reported_files_are_three_distinct_files(feed_server: str, tmp_path: Path) -> None:
    ledger = _books(tmp_path, feed_server, "btc-usd.beancount")

    data = _json(tmp_path, feed_server, ledger, "price", "export", "--output", str(tmp_path / "out"))

    assert isinstance(data, dict)
    files = [Path(name) for name in data["files"]]
    assert len(files) == 3
    assert len({(path.stat().st_dev, path.stat().st_ino) for path in files}) == 3, files


def test_two_feeds_whose_aliases_differ_only_by_case_get_two_files(feed_server: str, tmp_path: Path) -> None:
    lower = "; alias: btc-usd\n; commodity: BTC\n; quote: USD\n2026-09-11 price BTC 113000.00 USD\n"
    _FeedHandler.routes["/prices/btc-usd"] = {"body": lower.encode("utf-8"), "headers": {"ETag": '"r2"'}}
    ledger = _books(tmp_path, feed_server, "manual.beancount", feeds=("BTC-USD", "btc-usd"))

    out = _export(tmp_path, feed_server, ledger)

    assert _names(out / "prices") == ["BTC-USD.beancount", "btc-usd-managed.beancount", "manual.beancount"]
    assert "113000.00" in (out / "prices" / "btc-usd-managed.beancount").read_text()
    assert FEED_PRICE in (out / "prices" / "BTC-USD.beancount").read_text()
    assert _price_numbers(tmp_path, feed_server, out / "main.bean") == _price_numbers(tmp_path, feed_server, ledger)
    assert _stock_check(out / "main.bean").returncode == 0


def test_an_exact_case_name_exports_as_before(feed_server: str, tmp_path: Path) -> None:
    """The control (w3/413): the copy keeps its name and the feed takes `-managed`."""
    ledger = _books(tmp_path, feed_server, "BTC-USD.beancount")

    out = _export(tmp_path, feed_server, ledger)

    assert _names(out / "prices") == ["BTC-USD-managed.beancount", "BTC-USD.beancount"]
    assert (out / "prices" / "BTC-USD.beancount").read_text() == LOCAL_PRICES
    assert _price_numbers(tmp_path, feed_server, out / "main.bean") == _price_numbers(tmp_path, feed_server, ledger)


def test_an_unrelated_local_name_leaves_the_feed_its_plain_name(feed_server: str, tmp_path: Path) -> None:
    ledger = _books(tmp_path, feed_server, "manual.beancount")

    out = _export(tmp_path, feed_server, ledger)

    assert _names(out / "prices") == ["BTC-USD.beancount", "manual.beancount"]
