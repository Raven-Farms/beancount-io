"""Create a starter personal ledger — the accounting side of `bea init`.

The frontend owns prompts and next-step messaging; this module builds the
template, aligns it, validates it, and creates the file atomically.
"""

from __future__ import annotations

import datetime
import os
from decimal import MAX_PREC, Decimal, localcontext
from pathlib import Path
from typing import Any

from bea_engine import stopping
from bea_engine.amounts import parse_decimal_number
from bea_engine.ledger import write as ledger_write
from bea_engine.protocol import AuthError, ConflictError, UsageError

ACCOUNTS = (
    "Assets:Checking",
    "Assets:Savings",
    "Assets:Cash",
    "Liabilities:CreditCard",
    "Income:Salary",
    "Income:Interest",
    "Expenses:Groceries",
    "Expenses:Dining",
    "Expenses:Rent",
    "Expenses:Transport",
    "Expenses:Utilities",
    "Expenses:Fees",
    # `bea import` books every uncategorized row here, so a fresh ledger can
    # take an export without a second `bea add open` first.
    "Expenses:Uncategorized",
    "Equity:OpeningBalances",
)


def answer(
    file: Path,
    *,
    currency: str,
    date: str,
    opening_balances: list[str] | None = None,
) -> dict[str, Any]:
    """Write a new starter ledger at `file` and answer what was created.

    `opening_balances` are `'ACCOUNT NUMBER'` strings for template asset or
    liability accounts. The file must not already exist; creation is atomic
    (`os.link` of a validated candidate) so a race never overwrites.
    """
    file = file.expanduser()
    if not file.is_absolute():
        file = file.resolve()
    if file.exists() or file.is_symlink():
        raise ConflictError(f"Already exists: {file}. Choose a new path; init never overwrites a ledger.")

    currency = currency.strip().upper()
    try:
        day = datetime.date.fromisoformat(date)
    except ValueError as exc:
        raise UsageError(f"--date must be a date in YYYY-MM-DD form, not {date!r}.") from exc

    balances: dict[str, Decimal] = {}
    for balance in opening_balances or []:
        parts = balance.split()
        if len(parts) != 2 or parts[0] not in ACCOUNTS or not parts[0].startswith(("Assets:", "Liabilities:")):
            raise UsageError(
                "Opening balance must be 'ACCOUNT NUMBER' for one of the template's asset/liability accounts."
            )
        account, number = parts
        if account in balances:
            raise UsageError(f"Opening balance specified twice for {account}.")
        try:
            amount = parse_decimal_number(number)
        except ValueError as exc:
            raise UsageError(str(exc)) from exc
        balances[account] = amount

    content = f'option "title" "Personal ledger"\noption "operating_currency" "{currency}"\n\n'
    content += "; Add more accounts with bea add open. Amounts on credit accounts are negative.\n"
    content += "; bea import books rows it cannot categorize to Expenses:Uncategorized with flag '!'.\n"
    # Only the accounts that hold money are limited to the operating currency.
    # A category records what was spent, and on a restricted one an ordinary
    # foreign charge (`45 EUR @ 1.10 USD`) was refused (w5/363).
    content += "".join(
        f"{day} open {account} {currency}\n"
        if account.startswith(("Assets:", "Liabilities:"))
        else f"{day} open {account}\n"
        for account in ACCOUNTS
    )
    nonzero = {account: amount for account, amount in balances.items() if amount}
    if nonzero:
        content += f'\n{day} * "Opening balances"\n'
        # Fixed-point text: str(Decimal) turns a one-satoshi balance into
        # `1E-8`, which Beancount cannot parse as an amount.
        content += "".join(f"  {account}  {amount:f} {currency}\n" for account, amount in nonzero.items())
        # Exact, like the typed legs: the default 28-digit context rounded a
        # wider balance's negation, so the equity leg did not cancel it (w5/310).
        with localcontext() as exact:
            exact.prec = MAX_PREC
            total = sum(nonzero.values(), Decimal(0))
        content += f"  Equity:OpeningBalances  {total.copy_negate():f} {currency}\n"
    else:
        content += (
            "\n; Record opening balances with a transaction against Equity:OpeningBalances.\n"
            f'; {day} * "Opening balance"\n'
            f";   Assets:Checking          1000.00 {currency}\n"
            f";   Equity:OpeningBalances  -1000.00 {currency}\n"
        )

    from beancount.scripts.format import align_beancount

    content = align_beancount(content)  # type: ignore[no-untyped-call]
    _make_parent(file)
    with ledger_write.candidate_file(file, content) as candidate:
        ledger_write.validate_candidate(candidate, file)
        stopping.check()
        try:
            # Atomic creation without replacing a file another process created.
            os.link(candidate, file)
        except FileExistsError as exc:
            raise ConflictError(f"Already exists: {file}; nothing was overwritten.") from exc

    return {
        "created": str(file),
        "currency": currency,
        "date": day.isoformat(),
        "accounts": list(ACCOUNTS),
    }


def _make_parent(file: Path) -> None:
    """Create the new ledger's directory, or say plainly what stands in the way.

    `mkdir` raised straight through: a regular file where a directory was
    named read as `FileExistsError: [Errno 17]`, and a read-only parent as
    `PermissionError: [Errno 13]`, each with exit 1 as if a ledger had failed
    validation. The first is a bad argument and the second the filesystem
    refusing — on the first command a newcomer runs.
    """
    parent = file.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except (FileExistsError, NotADirectoryError) as exc:
        # `exists()` follows a link, so a dangling one (an unmounted drive) was
        # skipped and its parent, a real directory, blamed instead (w5/580).
        blocker = next((path for path in (parent, *parent.parents) if os.path.lexists(path)), parent)
        if blocker.is_symlink() and not blocker.exists():
            raise UsageError(
                f"Cannot create a ledger in {parent}: {blocker} is a broken symbolic link to "
                f"{os.readlink(blocker)}. Reconnect what it points to, or choose another directory. "
                "Nothing was written."
            ) from exc
        raise UsageError(
            f"Cannot create a ledger in {parent}: {blocker} is a file, not a directory. "
            "Choose another directory. Nothing was written."
        ) from exc
    except PermissionError as exc:
        existing = next((path for path in parent.parents if path.exists()), parent)
        raise AuthError(
            f"Cannot create {parent}: the directory {existing} is not writable. Nothing was written."
        ) from exc
