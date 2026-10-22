"""Reordered metadata or allowed currencies are the same directive on import (w5/916).

The comparison used the printed text, so swapping two metadata keys made a
note, event, balance or document import again, and the same swap on an
`open`, `commodity` or `close` made the repeat invalid; an opening's currency
list compared in order though it is a set.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_import_source_facts import _bea, _written

LEDGER = 'option "operating_currency" "USD"\n2024-01-01 open Assets:Cash USD\n'
NOTE = """import datetime, json
from pathlib import Path
from beancount.core import data

class Imp:
    def identify(self, path): return path.endswith(".json")
    def account(self, path): return "Assets:Cash"
    def extract(self, path, existing):
        meta = data.new_metadata(path, 1)
        meta.update(json.loads(Path(path).read_text()))
        day = datetime.date(2024, 2, 1)
        return [data.Note(meta, day, "Assets:Cash", "Monthly statement", frozenset(), frozenset())]

CONFIG = [Imp()]
"""
OPEN = """import datetime, json
from pathlib import Path
from beancount.core import data

class Imp:
    def identify(self, path): return path.endswith(".json")
    def account(self, path): return "Assets:Broker"
    def extract(self, path, existing):
        currencies = json.loads(Path(path).read_text())["currencies"]
        return [data.Open(data.new_metadata(path, 1), datetime.date(2024, 2, 1), "Assets:Broker", currencies, None)]

CONFIG = [Imp()]
"""
RUN = ["import", "statement.json", "--config", "importers.py", "--apply"]


def _start(tmp_path: Path, importer: str, payload: dict[str, object]) -> None:
    (tmp_path / "main.bean").write_text(LEDGER)
    (tmp_path / "importers.py").write_text(importer)
    _write(tmp_path, payload)


def _write(tmp_path: Path, payload: dict[str, object] | str) -> None:
    (tmp_path / "statement.json").write_text(payload if isinstance(payload, str) else json.dumps(payload))


def test_reordered_metadata_is_a_duplicate_note(tmp_path: Path) -> None:
    _start(tmp_path, NOTE, {})
    _write(tmp_path, '{"provider":"Example Bank","reference":"Jan-2024"}')
    assert _written(_bea(tmp_path, *RUN)) == 1
    first = (tmp_path / "main.bean").read_bytes()

    _write(tmp_path, '{"reference":"Jan-2024","provider":"Example Bank"}')
    preview = json.loads(_bea(tmp_path, "import", "statement.json", "--config", "importers.py").stdout)["data"]

    assert (preview["duplicates"], preview["ready"]) == (1, 0)
    assert _written(_bea(tmp_path, *RUN)) == 0
    assert (tmp_path / "main.bean").read_bytes() == first


def test_a_changed_metadata_value_is_still_a_new_note(tmp_path: Path) -> None:
    _start(tmp_path, NOTE, {})
    _write(tmp_path, '{"provider":"Example Bank","reference":"Jan-2024"}')
    assert _written(_bea(tmp_path, *RUN)) == 1

    _write(tmp_path, '{"reference":"Feb-2024","provider":"Example Bank"}')

    assert _written(_bea(tmp_path, *RUN)) == 1


@pytest.mark.parametrize(
    ("first", "second"),
    [(["USD", "EUR"], ["EUR", "USD"]), (["USD", "USD"], ["USD"])],
    ids=["reordered", "repeated"],
)
def test_the_same_allowed_currencies_are_a_duplicate_opening(
    tmp_path: Path, first: list[str], second: list[str]
) -> None:
    _start(tmp_path, OPEN, {"currencies": first})
    assert _written(_bea(tmp_path, *RUN)) == 1
    before = (tmp_path / "main.bean").read_bytes()

    _write(tmp_path, {"currencies": second})
    preview = json.loads(_bea(tmp_path, "import", "statement.json", "--config", "importers.py").stdout)["data"]

    assert (preview["duplicates"], preview["invalid"]) == (1, 0)
    assert _written(_bea(tmp_path, *RUN)) == 0
    assert (tmp_path / "main.bean").read_bytes() == before


def test_a_different_currency_set_is_still_a_different_opening(tmp_path: Path) -> None:
    _start(tmp_path, OPEN, {"currencies": ["USD"]})
    assert _written(_bea(tmp_path, *RUN)) == 1
    _write(tmp_path, {"currencies": ["EUR"]})

    refused = _bea(tmp_path, *RUN)

    assert refused.returncode == 1, refused.stdout
