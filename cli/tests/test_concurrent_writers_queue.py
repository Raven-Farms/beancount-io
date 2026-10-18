"""Unrelated `bea` writes started together queue instead of failing with exit 4 (w5/183).

`add price`, `add transaction` with an inferred currency, `add transactions`
and `import --apply` read the ledger to decide what to write. They read before
taking the write lock, so the append — which verifies that read under the lock —
refused whatever the writer it had just waited for committed. Eight prices for
eight different commodities mostly failed with "The ledger changed during the
operation … retry", though nothing conflicted. The decision is now made under
the lock; an edit that takes no lock is still a conflict.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]

LEDGER = """\
option "operating_currency" "USD"
2024-01-01 open Assets:Cash USD
2024-01-01 open Expenses:Food USD
"""
COMMODITIES = ("QQA", "QQB", "QQC", "QQD", "QQE", "QQF", "QQG", "QQH")
CSV = "Date,Amount,Description\n2024-02-03,-7.00,IMPORTED ROW\n"
ROWS = [
    {
        "date": "2024-02-02",
        "narration": f"bulk{number}",
        "postings": [
            {"account": "Expenses:Food", "amount": f"{number}.00 USD"},
            {"account": "Assets:Cash", "amount": f"-{number}.00 USD"},
        ],
    }
    for number in (1, 2)
]


def _env(tmp_path: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BEA_") and k != "CI"}
    env.update(
        BEA_CONFIG_DIR=str(tmp_path / "config"),
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        BEA_NO_UPDATE_NOTIFIER="1",
        PYTHONPATH=str(ROOT / "src"),
        NO_COLOR="1",
    )
    return env


def _ledger(tmp_path: Path) -> Path:
    ledger = tmp_path / "main.bean"
    ledger.write_text(LEDGER, encoding="utf-8")
    return ledger


def _race(tmp_path: Path, ledger: Path, runs: list[list[str]]) -> list[tuple[int, str, str]]:
    """Start every run at once and return each one's exit code, stdout and stderr."""
    env = _env(tmp_path)
    processes = [
        subprocess.Popen(
            [sys.executable, "-m", "cli.main", "--json", "--file", str(ledger), *args],
            env=env,
            cwd=tmp_path,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for args in runs
    ]
    results = []
    for process in processes:
        try:
            out, err = process.communicate(timeout=240)
        except subprocess.TimeoutExpired:
            for other in processes:
                other.kill()
            raise
        results.append((process.returncode, out, err))
    return results


def _report(results: list[tuple[int, str, str]]) -> str:
    return "\n".join(f"exit {code}: {out.strip()} {err.strip()}" for code, out, err in results)


def _price(commodity: str) -> list[str]:
    return ["add", "price", "--date", "2024-03-01", "--commodity", commodity, "--amount", "1 USD"]


def _transaction(number: int, amount: str) -> list[str]:
    return [
        "add",
        "transaction",
        f"n{number}",
        "--date",
        "2024-02-01",
        "-p",
        f"Expenses:Food {amount}",
        "-p",
        "Assets:Cash",
    ]


def test_prices_for_different_commodities_all_land(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)

    results = _race(tmp_path, ledger, [_price(commodity) for commodity in COMMODITIES])

    assert [code for code, _, _ in results] == [0] * len(COMMODITIES), _report(results)
    text = ledger.read_text(encoding="utf-8")
    for commodity in COMMODITIES:
        assert text.count(f"2024-03-01 price {commodity} ") == 1, text


@pytest.mark.parametrize(
    "amounts",
    [
        pytest.param([f"{number}.00" for number in range(1, 7)], id="inferred-currency"),
        pytest.param([f"{number}.00 USD" for number in range(1, 7)], id="explicit-currency"),
    ],
)
def test_transactions_all_land_however_the_currency_is_given(tmp_path: Path, amounts: list[str]) -> None:
    """The explicit spelling never read the ledger first; it is the control that always passed."""
    ledger = _ledger(tmp_path)

    results = _race(tmp_path, ledger, [_transaction(number, amount) for number, amount in enumerate(amounts, 1)])

    assert [code for code, _, _ in results] == [0] * len(amounts), _report(results)
    text = ledger.read_text(encoding="utf-8")
    for number in range(1, len(amounts) + 1):
        assert text.count(f'"n{number}"') == 1, text


def test_a_batch_and_an_import_queue_behind_single_adds(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    ledger.write_text(LEDGER + "2024-01-01 open Expenses:Uncategorized USD\n", encoding="utf-8")
    (tmp_path / "rows.json").write_text(json.dumps(ROWS), encoding="utf-8")
    (tmp_path / "bank.csv").write_text(CSV, encoding="utf-8")
    runs = [
        ["add", "transactions", "--from", str(tmp_path / "rows.json"), "--partial"],
        [
            "import",
            str(tmp_path / "bank.csv"),
            "--csv",
            "date=Date,amount=Amount,narration=Description",
            "--account",
            "Assets:Cash",
            "--duplicates",
            "include",
            "--apply",
        ],
        *(_price(commodity) for commodity in COMMODITIES[:4]),
    ]

    results = _race(tmp_path, ledger, runs)

    assert [code for code, _, _ in results] == [0] * len(runs), _report(results)
    text = ledger.read_text(encoding="utf-8")
    assert text.count('"bulk1"') == text.count('"bulk2"') == text.count("IMPORTED ROW") == 1, text
    assert text.count(" price ") == 4, text


def test_identical_prices_still_write_once(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)

    results = _race(tmp_path, ledger, [_price("QQA")] * 4)

    assert [code for code, _, _ in results] == [0] * 4, _report(results)
    payloads = [json.loads(out)["data"] for _, out, _ in results]
    assert sorted(payload["written"] for payload in payloads) == [0, 0, 0, 1], _report(results)
    assert all(payload["duplicate"] for payload in payloads if not payload["written"]), _report(results)
    assert ledger.read_text(encoding="utf-8").count(" price QQA ") == 1


def test_a_conflicting_quote_that_landed_first_is_still_refused(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    quotes = [[*_price("QQA")[:-1], amount] for amount in ("1 USD", "2 USD")]

    results = _race(tmp_path, ledger, quotes)

    assert sorted(code for code, _, _ in results) == [0, 4], _report(results)
    refused = next(err for code, _, err in results if code == 4)
    assert "Pass --force to record another quote" in refused, _report(results)
    assert ledger.read_text(encoding="utf-8").count(" price QQA ") == 1


@pytest.mark.parametrize(
    ("directive_type", "request_"),
    [
        pytest.param(
            "price",
            {"date": "2024-03-01", "currency": "QQA", "number": "1", "amount_currency": "USD"},
            id="price",
        ),
        pytest.param(
            "transaction",
            {"date": "2024-02-01", "narration": "n1", "postings": ["Expenses:Food 1.00", "Assets:Cash"]},
            id="inferred-currency",
        ),
    ],
)
def test_an_edit_that_takes_no_lock_is_still_a_conflict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, directive_type: str, request_: dict[str, Any]
) -> None:
    """The control: an editor saving right after the decision read gets exit 4, and keeps its edit."""
    from bea_engine import managed_load, protocol
    from bea_engine.ledger import adding

    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    ledger = _ledger(tmp_path)
    load = managed_load.load_file
    edits: list[int] = []

    def read_then_lose_the_race(*args: Any, **kwargs: Any) -> Any:
        loaded = load(*args, **kwargs)
        if not edits:
            edits.append(1)
            with ledger.open("a", encoding="utf-8") as handle:
                handle.write("2024-03-02 price ZZZ 9 USD\n")
        return loaded

    monkeypatch.setattr(managed_load, "load_file", read_then_lose_the_race)

    with pytest.raises(protocol.ConflictError, match="changed"):
        adding.answer(ledger, directive_type, request_)

    assert ledger.read_text(encoding="utf-8") == LEDGER + "2024-03-02 price ZZZ 9 USD\n"


def test_the_lock_is_released_after_a_command_took_it_twice(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keeping a held lock must not leave it held: the next writer in this process locks afresh."""
    from bea_engine.ledger import adding, write

    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    ledger = _ledger(tmp_path)

    for commodity in ("QQA", "QQB"):
        answer = adding.answer(
            ledger, "price", {"date": "2024-03-01", "currency": commodity, "number": "1", "amount_currency": "USD"}
        )
        assert answer["written"] == 1
        assert write._HELD_LOCKS == set()

    probe = (
        "import fcntl, os, sys\n"
        "from pathlib import Path\n"
        "from bea_engine.ledger import write\n"
        "path = write.cache_dir() / 'locks' / f'{write._lock_key(Path(sys.argv[1]))}.lock'\n"
        "fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)\n"
        "fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
    )
    free = subprocess.run(
        [sys.executable, "-c", probe, str(ledger)],
        env=_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=60,
        stdin=subprocess.DEVNULL,
    )
    assert free.returncode == 0, free.stderr


def test_a_command_that_writes_nothing_leaves_no_lock_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Queueing before the read must not make a duplicate or a refusal leave a file behind."""
    from bea_engine import protocol
    from bea_engine.ledger import adding

    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    ledger = _ledger(tmp_path)
    ledger.write_text(LEDGER + "2024-03-01 price QQA 1 USD\n", encoding="utf-8")
    locks = tmp_path / "cache" / "bea" / "locks"
    request = {"date": "2024-03-01", "currency": "QQA", "number": "1", "amount_currency": "USD"}

    assert adding.answer(ledger, "price", request)["duplicate"] is True
    with pytest.raises(protocol.ConflictError, match="Pass --force"):
        adding.answer(ledger, "price", {**request, "number": "2"})
    assert list(locks.iterdir()) == []

    assert adding.answer(ledger, "price", {**request, "currency": "QQB"})["written"] == 1
    kept = list(locks.iterdir())
    assert len(kept) == 1
    # A lock file a writer left is not this command's to remove.
    assert adding.answer(ledger, "price", request)["duplicate"] is True
    assert list(locks.iterdir()) == kept


def test_a_writer_queued_on_a_removed_lock_file_locks_its_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bea_engine.ledger import write

    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    ledger = _ledger(tmp_path)
    path = write.cache_dir() / "locks" / f"{write._lock_key(ledger)}.lock"
    probe = (
        "import os, sys\n"
        "from pathlib import Path\n"
        "from bea_engine.ledger import write\n"
        "print('waiting', flush=True)\n"
        "with write.lock_file(Path(sys.argv[1])):\n"
        "    path = write.cache_dir() / 'locks' / f'{write._lock_key(Path(sys.argv[1]))}.lock'\n"
        "    print(os.stat(path).st_ino, flush=True)\n"
    )

    with write.lock_file(ledger, deciding=True):
        waiter = subprocess.Popen(
            [sys.executable, "-c", probe, str(ledger)],
            env=_env(tmp_path),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert waiter.stdout is not None and waiter.stdout.readline().strip() == "waiting"
        with pytest.raises(subprocess.TimeoutExpired):
            waiter.wait(timeout=3)
    # Nothing was written under the deciding lock, so its file went with it and
    # the waiter, woken on the removed file, took a fresh one at the same path.
    out, err = waiter.communicate(timeout=60)

    assert waiter.returncode == 0, err
    assert path.exists()
    assert int(out.strip()) == path.stat().st_ino
