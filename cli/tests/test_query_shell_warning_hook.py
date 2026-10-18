"""A one-shot text query gives `warnings.showwarning` back, so its entries are freed (w5/575).

Upstream's shell installs its own method as the warnings hook, which kept the
shell and every loaded entry alive until interpreter shutdown: a text query on
a large ledger took about twice as long as `--json`, all of it teardown.
"""

from __future__ import annotations

import gc
import warnings
import weakref
from pathlib import Path

import pytest

from bea_engine import query

LEDGER = (
    "2024-01-01 open Assets:Cash USD\n2024-01-01 open Expenses:Food USD\n"
    '2024-01-02 * "x"\n  Expenses:Food  1 USD\n  Assets:Cash\n'
)


def test_the_hook_is_restored_and_the_shell_released(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER)
    before = warnings.showwarning
    shells: list[weakref.ref[object]] = []
    real = query.build_shell

    def recording(*args: object, **kwargs: object) -> object:
        shell = real(*args, **kwargs)  # type: ignore[arg-type]
        shells.append(weakref.ref(shell))
        return shell

    monkeypatch.setattr(query, "build_shell", recording)

    answer = query.text_answer(ledger, "SELECT account")

    assert "Expenses:Food" in answer["text"]
    assert warnings.showwarning is before
    gc.collect()
    assert shells and shells[0]() is None, "the one-shot shell should be freed once the answer is built"
