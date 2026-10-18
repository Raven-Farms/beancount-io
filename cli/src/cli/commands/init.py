"""Create a small, usable personal ledger without installing another tool.

Starter content, alignment, validation, and atomic creation run in
`bea-engine init`. This module owns prompts, option checks, and next-step UX.
"""

from __future__ import annotations

import datetime
import os
import re
import shlex
from decimal import Decimal
from pathlib import Path
from typing import Annotated

import typer

from cli import context, output
from cli.amounts import parse_decimal_number
from cli.errors import ConflictError, UsageError
from cli.utils import parse_date

# Must match `bea_engine.initiating.ACCOUNTS` — the engine builds the template;
# the frontend only uses this list to validate interactive opening balances.
_ACCOUNTS = (
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
    "Expenses:Uncategorized",
    "Equity:OpeningBalances",
)


#: A Beancount commodity symbol, as the loader spells one. This is upstream's
#: `CURRENCY_RE` minus its leading-`/` commodity-pair alternative, which is not
#: an operating currency: one uppercase letter, then anything from the symbol
#: alphabet, ending on a word character. Upstream ends its pattern with `\b`,
#: which is why `X_` is a symbol and `A.` is not — and why the last character is
#: *optional*, so `F` and `C` are symbols too. Requiring two characters refused
#: single-letter tickers that the loader accepts and `bea check` validates.
#: Restated rather than imported: the frontend loads no Beancount, and
#: `tests/test_init_currency_symbols.py` pins it against upstream's own regex.
_CURRENCY_SYMBOL = re.compile(r"[A-Z](?:[A-Z0-9'._-]*[A-Z0-9_])?")


def _currency(value: str) -> str:
    currency = value.strip().upper()
    if not _CURRENCY_SYMBOL.fullmatch(currency):
        raise typer.BadParameter(f"Invalid operating currency: {currency!r}. Use a symbol such as USD or EUR.")
    return currency


def _opening_amount(value: str) -> Decimal:
    try:
        return parse_decimal_number(value)
    except UsageError as exc:
        # Typer retries this question for an invalid interactive answer.
        raise typer.BadParameter(str(exc)) from exc


def _shell_path(shown: str) -> str:
    """Quote a path for a copy-pasteable command, leaving a leading `~` for the shell to expand."""
    if shown == "~":
        return shown
    if shown.startswith("~/"):
        return "~/" + shlex.quote(shown[2:])
    return shlex.quote(shown)


def _in_working_directory(file: Path) -> bool:
    """Whether `file` is the `main.bean` a bare `bea` run here would discover.

    A working directory that was deleted or cannot be read holds no ledger;
    the one just created is then reached by its path.
    """
    try:
        return file == Path.cwd() / "main.bean"
    except OSError:
        return False


def init(
    directory: Annotated[Path, typer.Argument(help="New ledger directory, or a .bean/.beancount file")] = Path("."),
    currency: Annotated[
        str | None, typer.Option("--currency", "-c", help="Operating currency, e.g. USD or EUR")
    ] = None,
    date: Annotated[
        str | None,
        typer.Option("--date", help="Earliest history/opening date YYYY-MM-DD; prompts interactively, otherwise today"),
    ] = None,
    opening_balance: Annotated[
        list[str] | None,
        typer.Option("--opening-balance", help="'ACCOUNT NUMBER' in the operating currency; repeat for each account"),
    ] = None,
) -> None:
    """Create main.bean with common accounts.

    Optional opening balances included. For unattended use:
    bea --no-input init books --currency USD.
    Credit card debt uses a negative opening balance.
    New ledger files are private (0600 on POSIX); chmod explicitly to share.
    """
    from cli.config import DEFAULT_ENTRY_FILE_FALLBACKS
    from cli.engine import launch

    ctx = context.current()
    if ctx.file is not None:
        if directory != Path("."):
            raise UsageError("Choose either --file or an init directory, not both.")
        file = ctx.file.expanduser().absolute()
    else:
        directory = directory.expanduser().absolute()
        file = directory if directory.suffix in {".bean", ".beancount"} else directory / "main.bean"
    # Before anything is created: every later command refuses such a path
    # (w5/315), and `$HOME/books` left an empty `./$HOME/books/` behind (w5/579).
    context.refuse_expanding_ledger_path(str(file))
    if file.exists() or file.is_symlink():
        raise ConflictError(f"Already exists: {file}. Choose a new path; init never overwrites a ledger.")
    # Refuse shadowing a sibling default root ledger (cwd discovery prefers main.bean).
    if file.name in {name.name for name in DEFAULT_ENTRY_FILE_FALLBACKS}:
        for sibling_name in DEFAULT_ENTRY_FILE_FALLBACKS:
            sibling = file.with_name(sibling_name.name)
            if sibling == file:
                continue
            if sibling.exists() or sibling.is_symlink():
                raise ConflictError(
                    f"Already exists: {sibling}. Init would create {file} and cwd discovery "
                    f"would prefer main.bean over main.beancount — choose a new path; init never "
                    f"shadows an existing root ledger."
                )
    # Every option is checked before the first question, naming itself: a bad
    # `--date` or `--opening-balance` was refused only after the prompts were
    # answered, as `Invalid value: …` with no option named (w5/588).
    given_day = None
    if date is not None:
        try:
            given_day = parse_date(date)
        except typer.BadParameter as exc:
            raise UsageError(f"--date {date!r}: {exc.message}") from None
    balances: dict[str, Decimal] = {}
    for balance in opening_balance or []:
        parts = balance.split()
        if len(parts) != 2 or parts[0] not in _ACCOUNTS or not parts[0].startswith(("Assets:", "Liabilities:")):
            raise UsageError(
                f"--opening-balance {balance!r}: Opening balance must be 'ACCOUNT NUMBER' for one of the "
                "template's asset/liability accounts."
            )
        account, number = parts
        if account in balances:
            raise UsageError(f"--opening-balance {balance!r}: Opening balance specified twice for {account}.")
        try:
            balances[account] = _opening_amount(number)
        except typer.BadParameter as exc:
            raise UsageError(f"--opening-balance {balance!r}: {exc.message}") from None
    prompted = currency is None
    if currency is None:
        if not ctx.can_prompt:
            raise UsageError("Choose an operating currency with --currency USD (or EUR, etc.).")
        currency = ctx.prompt("Operating currency", default="USD", value_proc=_currency)
    currency = _currency(currency)
    warnings = []
    if not re.fullmatch(r"[A-Z]{3}", currency):
        warnings.append(
            f"Operating currency {currency!r} is a valid Beancount symbol but is not three uppercase letters. "
            "Check for a typo (for example, USD). Custom and crypto symbols are supported."
        )
        if prompted:
            # Beside the answer it is about, before the next question, so a
            # typo can be caught before the ledger exists.
            output.note(warnings[-1])
    if date is None and ctx.can_prompt:
        day = ctx.prompt(
            "Earliest date you will record (opening balances must be as of this date)",
            default=datetime.date.today().isoformat(),
            value_proc=parse_date,
        )
    else:
        day = given_day or datetime.date.today()
    if ctx.can_prompt and opening_balance is None:
        balances["Assets:Checking"] = ctx.prompt(
            f"Checking opening balance on {day} (negative for an overdraft)", default="0", value_proc=_opening_amount
        )

    argv = ["init", "--file", str(file), "--currency", currency, "--date", day.isoformat()]
    for account, amount in balances.items():
        if amount:
            argv += ["--opening-balance", f"{account} {amount:f}"]
    data = launch.helper_json(argv, writes=True)
    if warnings:
        data["warnings"] = warnings
    if ctx.json_output:
        output.emit(data, target=output.file_target(file))
    else:
        if not prompted:
            for warning in warnings:
                output.note(warning)
        accounts = data.get("accounts") or list(_ACCOUNTS)
        output.success(f"Created {file} with {len(accounts)} accounts in {currency}.")
        try:
            shown = f"~/{file.relative_to(Path.home())}"
        except ValueError:
            shown = str(file)
        # Use the same target in every hint. A custom filename needs --file,
        # as does BEA_FILE overriding discovery after the suggested cd.
        bea = f"bea --file {_shell_path(shown)}" if os.environ.get("BEA_FILE") or file.name != "main.bean" else "bea"
        if bea != "bea":
            next_command = f"{bea} check"
        elif _in_working_directory(file):
            next_command = "bea check"
        else:
            next_command = f"cd {_shell_path(shown.rpartition('/')[0])} && bea check"
        typer.echo(f"Next: {next_command}")
        typer.echo(
            f"Accounts open on {day}. To record earlier history, edit their open dates; "
            "new ledgers can use init --date YYYY-MM-DD."
        )
        typer.echo(f"Record purchases with {bea} add transaction, or preview a bank export with {bea} import.")
