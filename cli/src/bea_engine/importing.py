"""Preview and apply bank-export entries — the accounting side of `bea import`.

The frontend owns option parsing, remembered importer/CSV paths, and the human
preview table. This module loads the ledger, runs a CSV mapper or configured
Beangulp importer, deduplicates, validates, and optionally appends.
"""

from __future__ import annotations

import copy
import difflib
import hashlib
import io
import os
import re
import runpy
import shlex
import sys
import tempfile
import unicodedata
from collections.abc import Iterator, Sequence
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass
from decimal import Context, Decimal
from pathlib import Path
from typing import Any

from bea_engine.ledger import write as ledger_write
from bea_engine.ledger.text import (
    bea_command,
    checked_operating_currencies,
    ledger_roots,
    reports_unused_accounts,
    unknown_root_message,
)
from bea_engine.ledger.writer import format_entry, nfc_entry_accounts, normalize_entry_strings
from bea_engine.protocol import ConflictError, EngineError, LedgerError, UsageError
from bea_engine.query import format_error

_IDENTITY_KINDS = {
    "bank_id": "bank",
    "fitid": "ofx",
    "transaction_id": "bank",
    "imported_id": "bank",
}

_DEFAULT_ID_KEYS = ["bank_id", "fitid", "transaction_id", "imported_id"]


@contextmanager
def _capturing(logs: io.StringIO) -> Iterator[None]:
    """Collect everything the importer prints into `importer_output`.

    `redirect_stdout` swaps only the Python objects; a `subprocess.run` or an
    `os.write(1, …)` inside the importer writes to the inherited descriptors,
    which bypassed the capture (w1/061). Descriptors 1 and 2 point at a
    scratch file for the duration and its bytes are appended afterwards.
    """
    with tempfile.TemporaryFile() as sink:
        saved: list[tuple[int, int]] = []
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.flush()
                fd = stream.fileno()
            except (AttributeError, OSError, ValueError):
                continue
            if fd in (1, 2) and all(fd != kept for kept, _ in saved):
                saved.append((fd, os.dup(fd)))
                os.dup2(sink.fileno(), fd)
        try:
            with redirect_stdout(logs), redirect_stderr(logs):
                yield
        finally:
            for fd, copy_fd in saved:
                os.dup2(copy_fd, fd)
                os.close(copy_fd)
            sink.seek(0)
            logs.write(sink.read().decode("utf-8", "replace"))


def _exited(exc: SystemExit, logs: io.StringIO) -> EngineError:
    """An importer configuration that called `sys.exit`, as the importer failure it is.

    A Beangulp ingest script reused as `--config` runs `Ingest(CONFIG)()`
    when it is loaded, and Click exits. `SystemExit` is no `Exception`, so it
    passed the importer guard, the engine answered nothing, and the frontend
    said the engine "did not answer" and, for `--apply`, that the outcome was
    unknown, though nothing had been written (w5/634).
    """
    status = "" if exc.code is None else f": {exc.code}"
    return _with_output(
        LedgerError(
            f"Importer failed (SystemExit{status}): the configuration called sys.exit, as an unguarded "
            'beangulp.Ingest(CONFIG)() does. Put that call under if __name__ == "__main__": to use the '
            "script with --config.",
            traceback=_traceback(exc),
        ),
        logs,
    )


def _with_output(error: EngineError, logs: io.StringIO) -> EngineError:
    """Attach what the importer printed before it failed to the failure.

    The prints leading up to an exception are what an importer author needs to
    find the bad row, and the capture that keeps them out of the envelope was
    also the only copy: they reached neither stderr nor `--debug` (w5/143).
    They travel as `result.importer_output`, the field a preview carries.
    """
    printed = logs.getvalue()
    if printed and error.result is None:
        error.result = {"importer_output": printed}
    return error


_METADATA_KEY = re.compile(r"[a-z][A-Za-z0-9_-]+")


def _effective_id_keys(id_keys: list[str] | None, *, csv_id_mapped: bool = False) -> list[str]:
    """Resolve `--id-key` values to metadata keys the CSV mapper actually writes.

    CSV `id=` always lands in `bank_id` metadata. Agents often pass `--id-key id`
    after naming the column that way; treat that alias as `bank_id` so bank-ID
    dedupe stays on instead of falling back to content hashes.

    The alias ignores case: a metadata key starts lowercase, so `ID` (the usual
    header spelling) can name nothing else. And a mapping with `id=` keeps
    `bank_id` whatever keys were typed, since that is the only key its rows
    carry: a list without it would turn the mapped ids off (w5/254).

    The default keys fold case the same way, so `FITID`, as OFX spells it,
    is `fitid`. Any other key a metadata key cannot be — empty, or not
    starting lowercase — is refused: it would replace the defaults with a
    key no entry carries and turn native-ID matching off (w5/469).
    """
    if not id_keys:
        return list(_DEFAULT_ID_KEYS)
    resolved: list[str] = []
    seen: set[str] = set()
    for key in [*id_keys, *(["bank_id"] if csv_id_mapped else [])]:
        folded = key.lower()
        # Only a spelling that cannot be a key folds: `fitId` and `bank_ID` are
        # keys a ledger may use, and folding them turned their matching off (w5/604).
        if folded == "id":
            mapped = "bank_id"
        elif _METADATA_KEY.fullmatch(key) or folded not in _DEFAULT_ID_KEYS:
            mapped = key
        else:
            mapped = folded
        if not _METADATA_KEY.fullmatch(mapped):
            raise UsageError(
                f"--id-key {key!r} is not a metadata key; a key starts with a lowercase letter and holds letters, "
                f"digits, '-' and '_', such as {', '.join(_DEFAULT_ID_KEYS)}."
            )
        if mapped not in seen:
            seen.add(mapped)
            resolved.append(mapped)
    return resolved


def answer(
    file: Path,
    source: Path,
    *,
    csv_mapping: str | None = None,
    csv_account: str | None = None,
    date_format: str | None = None,
    delimiter: str | None = None,
    encoding: str | None = None,
    rules_file: Path | None = None,
    default_account: str | None = None,
    config: Path | None = None,
    importer_name: str | None = None,
    apply: bool = False,
    duplicates: str = "review",
    id_keys: list[str] | None = None,
    into: Path | None = None,
    allow_errors: bool = False,
    config_source: str = "--config",
) -> dict[str, Any]:
    """Extract, review, optionally write, and answer with the preview payload.

    `duplicates` is `review`, `skip`, or `include`. Exact stable-ID matches are
    always skipped. Nothing is written unless `--apply` is set and the preview
    is free of conflicts / unresolved possible duplicates / validation errors.
    """
    from beancount.core.data import Open, Price, Transaction

    from bea_engine import managed_load
    from bea_engine.csv_mapper import CsvImporter, load_rules, parse_delimiter, parse_encoding, parse_mapping
    from bea_engine.ledger.reader import entry_generated, forget_source_lines

    if duplicates not in {"review", "skip", "include"}:
        raise UsageError(f"--duplicates must be review, skip, or include; got {duplicates!r}.")
    if csv_mapping is not None and config is not None:
        raise UsageError("Pass --csv or --config, not both.")
    # Refused before the ledger loads or the importer's extract() runs, which
    # may have side effects of its own (w5/604).
    _effective_id_keys(id_keys)

    file = Path(os.path.abspath(file))
    source = source.expanduser().resolve()
    if not source.is_file():
        raise UsageError(f"Export file not found: {source}")

    source_bytes = source.read_bytes()
    snapshot = ledger_write.LedgerSnapshot.capture(file)
    target = ledger_write.destination(file, into)
    original = snapshot.require_target(target)
    existing, errors, options = managed_load.load_file(file, snapshot=snapshot)
    # An account staged for this import under `nounused` is the one error the
    # import itself clears; validation still refuses a result that leaves it.
    if not allow_errors and not all(ledger_write.is_unused_open(error) for error in errors):
        raise LedgerError(
            f"Ledger has {len(errors)} error(s). Pass --allow-errors to preview and apply anyway.",
            details=[format_error(error, ledger_file=file) for error in errors],
        )

    logs = io.StringIO()
    notes: list[str] = []
    roots = ledger_roots(options)
    csv_mode = csv_mapping is not None
    skipped_blank = 0
    skipped_pending = 0
    csv_id_mapped = False
    if csv_mode:
        if csv_account is None or csv_mapping is None:
            raise UsageError("--csv needs --account ACCOUNT, naming the account the export belongs to.")
        mapping = parse_mapping(csv_mapping)
        csv_id_mapped = mapping.column("id") is not None
        # Before the preview, not after: an invalid name would otherwise block
        # every row with the wrong diagnosis instead of failing on the typo.
        csv_account = _valid_account(csv_account, "--account", roots)
        # The built-in fallback follows the ledger's expenses root: the literal
        # `Expenses:` name is refused on a ledger that sets `name_expenses`.
        if default_account is None:
            default_account = f"{roots[-1]}:Uncategorized"
            fallback = f"the built-in default account {default_account}"
        else:
            default_account = _valid_account(default_account, "--default-account", roots)
            fallback = f"--default-account {default_account}"
        # A counter posting to the source account cancels the bank movement:
        # `-100 USD` and `+100 USD` on Assets:Checking, written with exit 0
        # and gone from its balance (w5/468).
        if default_account == csv_account:
            raise UsageError(
                f"{fallback} is the --account being imported; an uncategorized row would post against its "
                "own source and cancel out. Name the account its money goes to or comes from."
            )
        rules = load_rules(Path(rules_file), roots) if rules_file is not None else None
        for number, listed in enumerate(rules or [], start=1):
            if listed.account == csv_account:
                raise UsageError(
                    f"Rules file {rules_file}: rule {number} (match {listed.pattern!r}) posts to {listed.account}, the "
                    "--account being imported; a matching row would post against its own source and cancel out. "
                    "Name the account its money goes to or comes from."
                )
        resolved_date_format = "%Y-%m-%d" if date_format is None else date_format
        resolved_delimiter = parse_delimiter(delimiter) if delimiter is not None else None
        resolved_encoding = parse_encoding(encoding) if encoding is not None else "utf-8"
        operating = options.get("operating_currency") or []
        importer: Any = CsvImporter(
            account=csv_account,
            mapping=mapping,
            date_format=resolved_date_format,
            rules=rules,
            default_account=default_account,
            currency=_row_currency(existing, csv_account, options, checked="currency" not in mapping.columns),
            known_currencies=_known_currencies(existing, operating),
            delimiter=resolved_delimiter,
            encoding=resolved_encoding,
            account_roots=roots,
        )
        preview_config = csv_mapping
        try:
            account = str(importer.account(str(source)))
            with _capturing(logs):
                entries = _extracted(importer, source, existing)
        except EngineError as exc:
            _with_output(exc, logs)
            raise
        except Exception as exc:
            raise _with_output(
                LedgerError(f"Importer failed ({type(exc).__name__}): {exc}.", traceback=_traceback(exc)), logs
            ) from exc
        skipped_blank = importer.skipped_blank_rows
        skipped_pending = len(importer.skipped_pending)
        if importer.skipped_pending:
            pending = "; ".join(importer.skipped_pending[:3]) + ("; …" if len(importer.skipped_pending) > 3 else "")
            notes.append(
                f"Left out {skipped_pending} pending row(s) ({pending}); import them from the export they post in."
            )
        if importer.pending_column is not None:
            column, count = importer.pending_column
            notes.append(
                f"Column {column!r} marks {count} row(s) pending, and they are imported as they are: a pending "
                f"charge that posts at another amount is then booked twice. Add status={column} to the --csv "
                "mapping to leave pending rows out until they post."
            )
        if importer.constant_currency is not None:
            notes.append(
                f"currency={importer.constant_currency} names no column of {source.name}, so every row "
                f"posts in {importer.constant_currency}."
            )
        if importer.rejected_categories:
            examples = ", ".join(repr(name) for name in list(importer.rejected_categories)[:3])
            count = sum(importer.rejected_categories.values())
            notes.append(
                f"{count} row(s) carry a category that is not an account name ({examples}); they post to "
                f"{default_account} with flag '!'. Categorize them with --rules, or map a column of full "
                "account names with --csv category=Column."
            )
        if importer.source_categories:
            notes.append(
                f"{importer.source_categories} row(s) carry the category {csv_account}, the account being imported, "
                f"so they post to {default_account} with flag '!' instead of cancelling out. Categorize them with "
                "--rules."
            )
    else:
        if config is None:
            raise UsageError("Choose a Python importer with --config FILE, or use --csv for a column mapping.")
        config = config.expanduser().resolve()
        preview_config = str(config)
        sys.path.insert(0, str(config.parent))
        try:
            with _capturing(logs):
                importer = _importer(config, source, importer_name)
                # NFC like the row accounts `_writable` normalizes, so an NFD
                # source account still finds its own legs (w5/530).
                account = unicodedata.normalize("NFC", str(importer.account(str(source))))
                entries = _extracted(importer, source, existing)
        except EngineError as exc:
            _with_output(exc, logs)
            raise
        except ImportError as exc:
            if not _is_missing_dependency(exc, config.parent):
                # A wrong name or a relative import is a mistake in the
                # configuration; nothing is missing, so nothing is to install.
                raise LedgerError(
                    f"Importer failed ({type(exc).__name__}): {exc}. The configuration runs as a script, so "
                    "a module beside it is imported by its plain name ('import helper'), not relatively.",
                    traceback=_traceback(exc),
                ) from exc
            # This handler runs inside the engine, so the module is missing from
            # the engine's environment — not from whatever launched `bea`.
            # Installing it beside the frontend changes nothing here.
            raise _with_output(
                UsageError(
                    f"Importer dependency is unavailable: {exc}. Importer configurations are executed by the "
                    "managed engine, not the environment you run bea from, so the package has to be installed "
                    "there; 'bea engine status' prints which engine serves and where it lives. "
                    "See docs/IMPORTING.md.",
                    traceback=_traceback(exc),
                ),
                logs,
            ) from exc
        except SystemExit as exc:
            raise _exited(exc, logs) from exc
        except Exception as exc:
            raise _with_output(
                LedgerError(f"Importer failed ({type(exc).__name__}): {exc}.", traceback=_traceback(exc)), logs
            ) from exc
        finally:
            sys.path.pop(0)

    entries = [_writable(entry, index + 1, importer, logs) for index, entry in enumerate(entries)]
    for index, entry in enumerate(entries):
        if isinstance(entry, Transaction) and not all(_has_explicit_units(p) for p in _source_legs(entry, account)):
            raise _with_output(
                LedgerError(
                    f"Importer {_name(importer)} row {index + 1} cannot be written as a ledger entry: its "
                    f"{account} posting has no amount. The importer must supply explicit source amounts."
                ),
                logs,
            )
    keys = _effective_id_keys(id_keys, csv_id_mapped=csv_id_mapped)
    identities: dict[tuple[str, str, str], Any] = {}
    fingerprints: dict[tuple[Any, ...], list[Any]] = {}
    open_currencies = _open_currencies(existing, Open)
    windows = _active_windows(existing)
    # Only what the ledger writes can be a duplicate: a forecast plugin's
    # projected copy made every real payment it predicted a "possible
    # duplicate" cited at the template's line, and `--duplicates skip` then
    # dropped them all (w5/325).
    forget_source_lines()
    written = [entry for entry in existing if not entry_generated(entry, type(entry).__name__.lower())]
    # Bank ids another account issued, reached here only through a transfer's
    # counter leg: never an exact match for this account's rows (w5/598).
    transfer_ids: dict[tuple[str, str, str], Any] = {}
    # Every entry under one bank id, not only the last: a reused reference
    # (w5/599) names several, and a row is the one nearest its date.
    dated: dict[tuple[str, str, str], list[Any]] = {}
    # Transfers another account's import wrote, by the amounts they post here:
    # each bank words its side differently, so only date and amount pair them (w5/600).
    counterparts: dict[tuple[str, ...], list[Any]] = {}
    for entry in written:
        entry = normalize_entry_strings(entry)
        if isinstance(entry, Transaction) and _source_legs(entry, account):
            elsewhere = _issued_elsewhere(entry, account, roots[:2])
            if elsewhere:
                counterparts.setdefault(_amounts_key(_fingerprint(entry, account)), []).append(entry)
            for identity in _identities(entry, account, keys):
                if elsewhere and _is_native_identity(identity):
                    transfer_ids[identity] = entry
                else:
                    identities[identity] = entry
                    dated.setdefault(identity, []).append(entry)
            _index_twin(fingerprints, entry, account, ledger=True)
    if source.read_bytes() != source_bytes:
        raise ConflictError("The export changed during extraction; nothing was written. Retry.")
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    other_entries = {_directive_text(entry) for entry in written if not isinstance(entry, Transaction | Price)}
    quotes = _written_quotes(existing)
    price_conflicts = False
    rows: list[dict[str, Any]] = []
    texts: list[str] = []
    conflicts = False
    # Which side a conflicting id came from: the ledger, or an earlier row of
    # this same export (banks do reuse ids within one file).
    ledger_conflicts = False
    batch_conflicts = False
    hashed = _hash_rows(entries, account, keys, Transaction)
    claimed, owners = _claim_payeeless_ids(hashed, identities, account)
    batch_rows: dict[int, int] = {}
    first_uses = _first_uses(entries, Transaction)
    stage_opens = reports_unused_accounts(options)
    # Blocked rows with what they were before the block, for the second look below.
    held: list[tuple[dict[str, Any], Any, str, str | None]] = []
    for index, entry in enumerate(entries):
        entry = normalize_entry_strings(entry)
        status, reason, match = "new", None, None
        id_source: str | None = None
        if isinstance(entry, Transaction):
            if not _source_legs(entry, account):
                posted = ", ".join(dict.fromkeys(p.account for p in entry.postings)) or "no account"
                raise LedgerError(
                    f"Importer row {index + 1} has no posting to its source account {account} or to an account "
                    f"under it; it posts to {posted}. The importer's account() must return an account the row "
                    "posts to, or a parent of one."
                )
            fingerprint = _fingerprint(entry, account)
            legacy_ids: list[str] = []
            if entry.meta.get("import-id"):
                id_source = "importer"
            else:
                native = _native_import_id(entry.meta, keys)
                if native is not None:
                    entry.meta["import-id"] = native
                    id_source = "bank"
                else:
                    row_ids = hashed[index]
                    entry.meta["import-id"] = row_ids.canonical
                    legacy_ids = claimed.get(index, [])
                    id_source = "hash"
            ids = _identities(entry, account, keys)
            legacy_keys = [(account, "import-id", value) for value in legacy_ids]
            legacy_keys += [(account, "digest", value.rsplit(":", 1)[1]) for value in legacy_ids]
            ids.extend(legacy_keys)
            lookup_only = set(legacy_keys)
            ids.append((account, "file", hashlib.sha256(f"{account}:{source_hash}:{index}".encode()).hexdigest()))
            # An older generated id is lookup-only *and* content-checked: that
            # format was lossy enough to hand two genuinely different rows one
            # digest, so a hit on it means "already imported" only when the
            # date and source amounts agree. Dropping the rest here, rather than
            # letting them reach the conflict test, is what keeps a reused
            # native id with changed source amounts a conflict.
            hits = [
                (key, found, same)
                for key in ids
                if (found := identities.get(key)) is not None
                # A stored narration-only id belongs to the row that claimed its
                # entry, whichever other row's own id happens to spell it.
                and not (id_source == "hash" and _is_generated_identity(key) and owners.get(id(found), index) != index)
                and (
                    (same := _same_row(key, found, account, fingerprint, lookup_only=key in lookup_only))
                    or key not in lookup_only
                )
            ]
            if hits:
                # A canonical digest proves the original source row even if
                # a retained file/native ID disagrees with later ledger edits.
                canonical = next(
                    (hit for hit in hits if hit[0] not in lookup_only and _is_generated_identity(hit[0])), None
                )
                if canonical is not None:
                    hits = [canonical]
                (_, kind, matched_value), match, _ = hits[0]
                if not all(same for _, _, same in hits):
                    status, conflicts = "conflict", True
                    if id(match) in batch_rows:
                        batch_conflicts = True
                        reason = (
                            f"Stable ID repeats row {batch_rows[id(match)]} of this import with different "
                            "transaction data."
                        )
                    else:
                        ledger_conflicts = True
                        reason = "Stable ID matches an entry with different transaction data."
                elif kind == "file":
                    status, reason = "duplicate", "Previously imported source row matches."
                elif kind == "digest":
                    stored = next(
                        (
                            str(value)
                            for value in (match.meta.get("import-id"), match.meta.get("import-id-2"))
                            if str(value or "").endswith(f":sha256:{matched_value}")
                        ),
                        f"sha256:{matched_value}",
                    )
                    status, reason = "duplicate", f"import-id {stored} is already in the ledger."
                else:
                    status, reason = "duplicate", f"import-id {matched_value} is already in the ledger."
                if status == "duplicate" and id(match) in batch_rows:
                    # The match is an earlier row of this export, so nothing is
                    # "already in the ledger". Two bank lines sharing a native
                    # ID on different dates — a monthly autopay reference — are
                    # evidence the column is not a unique transaction ID:
                    # review them, never drop one (w5/075). A same-day repeat
                    # with a tidier description stays one transaction.
                    earlier = batch_rows[id(match)]
                    reused = kind in {"bank", "import-id"} and not _is_generated_identity(hits[0][0])
                    if reused and match.date != entry.date:
                        status = "possible_duplicate"
                        reason = (
                            f"Stable ID {matched_value} repeats row {earlier} of this import on a different date; "
                            "a reference shared by separate transactions is not a unique ID."
                        )
                    else:
                        reason = f"Repeats row {earlier} of this import."
                elif status == "duplicate" and all(_is_native_identity(key) for key, _, _ in hits):
                    # Across exports too: a monthly autopay arrives one month
                    # per file, and February's rent was dropped as January's
                    # with exit 0 (w5/599). A date corrected in the ledger
                    # moves it days, not weeks, and stays the same row.
                    match = _nearest(dated.get(hits[0][0], [match]), entry, account, fingerprint)
                    days = abs((entry.date - match.date).days)
                    if days >= _REUSED_REFERENCE_DAYS:
                        status = "possible_duplicate"
                        reason = (
                            f"Stable ID {matched_value} is already in the ledger on {match.date}, {days} days from "
                            "this row; a reference reused on other dates, such as a monthly autopay's, is not a "
                            "unique ID."
                        )
            elif (other_side := _transfer_side(ids, transfer_ids, entry, account, fingerprint)) is not None:
                (_, _, matched_value), match = other_side
                status, reason = (
                    "possible_duplicate",
                    f"Stable ID {matched_value} is on the other side of a transfer from {match.postings[0].account} "
                    f"dated {_relative_days(match.date, entry.date)}, for the same amount; a bank that shares one "
                    "reference across both legs makes this that transfer.",
                )
            elif (twin := _possible_twin(fingerprints, entry, account, fingerprint, owners, index)) is not None:
                status, reason, match = (
                    "possible_duplicate",
                    _twin_reason(entry, twin, batch_rows.get(id(twin)), ours=id_source != "hash", keys=keys),
                    twin,
                )
            elif (counterpart := _transfer_counterpart(counterparts, entry, account, fingerprint)) is not None:
                status, reason, match = (
                    "possible_duplicate",
                    f"A transfer from {counterpart.postings[0].account} dated "
                    f"{_relative_days(counterpart.date, entry.date)} already posts {_source_amounts(entry, account)} "
                    f"to {account}; this row may be its other side, worded by this bank.",
                    counterpart,
                )
            if status == "new" or (status == "possible_duplicate" and duplicates == "include"):
                for identity in ids:
                    identities[identity] = entry
                    dated.setdefault(identity, []).append(entry)
                _index_twin(fingerprints, entry, account, ledger=False)
                batch_rows[id(entry)] = index + 1
        rule = entry.meta.pop("_csv_rule", None) if isinstance(entry, Transaction) else None
        text = format_entry(entry) if isinstance(entry, Transaction) else _directive_text(entry)
        if isinstance(entry, Price):
            # One quote per commodity and day, by value, as `add price` keeps
            # it: the text test wrote `111.00` beside a recorded `110.00`, and
            # `110.0` as if new, but skipped a quote `implicit_prices` made up
            # (w5/302).
            key = (entry.date, entry.currency, entry.amount.currency)
            recorded = quotes.setdefault(key, [])
            match = next((quote for quote in recorded if quote.amount.number == entry.amount.number), None)
            other = next((quote for quote in recorded if quote.amount.number != entry.amount.number), None)
            if match is not None:
                status, reason = "duplicate", f"Price already recorded at {_quote_origin(match, batch_rows)}."
            elif other is not None:
                status, conflicts, price_conflicts = "conflict", True, True
                match = other
                reason = (
                    f"{entry.currency} already has a {entry.date} price of {_plain_amount(other.amount)} at "
                    f"{_quote_origin(other, batch_rows)}; refusing {_plain_amount(entry.amount)}."
                )
            else:
                recorded.append(entry)
                batch_rows[id(entry)] = index + 1
        elif not isinstance(entry, Transaction):
            if text in other_entries:
                status, reason = "duplicate", "Identical directive already exists."
            other_entries.add(text)
        include = status == "new" or (status == "possible_duplicate" and duplicates == "include")
        unblocked = (status, reason)
        if include and _entry_accounts(entry):
            blocked_reason = _blocked_reason(
                entry,
                open_currencies,
                roots,
                first_uses,
                stage_opens,
                ledger=file,
                source=account if csv_mode else None,
                windows=windows,
            )
            if blocked_reason is not None:
                status, reason, include = "blocked", blocked_reason, False
        if include:
            texts.append(text)
        row_dict: dict[str, Any] = {
            "row": index + 1,
            "status": status,
            "reason": reason,
            "id_source": id_source,
            "include": include,
            "entry": text,
            "accounts": list(dict.fromkeys(name for name, _ in _entry_accounts(entry))),
            "date": entry.date.isoformat(),
            "payee": entry.payee if isinstance(entry, Transaction) else None,
            "narration": entry.narration if isinstance(entry, Transaction) else None,
            "amount": _source_amounts(entry, account) if isinstance(entry, Transaction) else "",
            "match": {
                "filename": match.meta.get("filename"),
                "lineno": match.meta.get("lineno"),
                "row": batch_rows.get(id(match)),
                "entry": format_entry(match),
            }
            if match
            else None,
        }
        if csv_mode:
            row_dict["rule"] = rule
        rows.append(row_dict)
        if status == "blocked":
            held.append((row_dict, entry, *unblocked))

    # The ledger before the import is not the whole answer to "is this account
    # open": `auto_accounts` opens whatever a transaction posts to, and an
    # importer may return the `open` beside its first transaction. Blocking on
    # the earlier ledger alone refused every row of a first import into such a
    # ledger, with an `add open` remedy its convention never writes, while
    # `bea add transaction` to the same account succeeded (w5/134). So the
    # accounts are read again from the ledger as the import would leave it.
    opened_after = open_currencies
    if any(name not in open_currencies for _, entry, _, _ in held for name, _ in _entry_accounts(entry)):
        proposed_rows = [row for row in rows if row["include"] or row["status"] == "blocked"]
        entries_after = _entries_after(
            snapshot, target, original, [row["entry"] for row in proposed_rows], [row["row"] for row in proposed_rows]
        )
        after = _open_currencies(entries_after, Open)
        windows_after = _active_windows(entries_after)
        opened_after = after
        for row_dict, entry, was, why in held:
            still = _blocked_reason(
                entry,
                after,
                roots,
                first_uses,
                stage_opens,
                ledger=file,
                source=account if csv_mode else None,
                windows=windows_after,
            )
            if still is None:
                row_dict.update(status=was, reason=why, include=True)
            else:
                row_dict["reason"] = still
        texts = [row["entry"] for row in rows if row["include"]]

    shown = [row["entry"] for row in rows if row["include"] or row["status"] == "blocked"]
    proposed = ledger_write.decoded_append(target, original, shown)
    validation_errors: list[str] = []
    validation_warnings: list[str] = []
    try:
        validation_warnings = ledger_write.validate_append(
            file, texts, allow_errors=allow_errors, into=into, snapshot=snapshot
        )
    except LedgerError as exc:
        # Only a validation failure belongs in the preview as text. Catching
        # every EngineError here flattened the class away, so a concurrent edit
        # — a ConflictError carrying category "conflict" and exit 4 — came back
        # as "Import would leave the ledger invalid" at exit 1, with "retry"
        # demoted to a details line. Worse, it was a coin flip: the same race
        # caught at the `append` call below propagates intact, so identical
        # commands reported the same situation two different ways and a retry
        # wrapper keyed on exit 4 worked about half the time. An auth or usage
        # failure from the same call loses its category the same way.
        validation_errors = exc.details or [str(exc)]
        # What `--allow-errors` tolerated still travels with the failure (w5/461).
        validation_warnings = list(exc.ledger_errors)
        # Errors the appended rows carry are those rows', as bulk add names
        # them: an unbalanced row previewed as `new`, counted ready, and
        # `--apply` refused the import naming no row (w5/638).
        named = _named_rows(file, texts, exc, allow_errors=allow_errors, into=into)
        if named:
            included = [row for row in rows if row["include"]]
            for position, lines in named.items():
                included[position].update(status="invalid", include=False, reason=" ".join(_unlocated(lines)))
            texts = [row["entry"] for row in rows if row["include"]]
            validation_errors = [f"Row {row['row']}: {row['reason']}" for row in rows if row["status"] == "invalid"]

    preview: dict[str, Any] = {
        "source": str(source),
        "config": preview_config,
        "config_source": config_source,
        "into": str(target),
        "importer": _name(importer),
        "account": account,
        "rows": rows,
        "ready": len(texts),
        "written": 0,
        "duplicates": sum(row["status"] == "duplicate" for row in rows),
        "possible_duplicates": sum(row["status"] == "possible_duplicate" for row in rows),
        # Conflicts were tracked only as the boolean that gates exit 4, so the
        # one status that forces a human to look was the one counted nowhere:
        # an all-conflict preview tallied as `0 ready, 0 … 0 …` and read as an
        # empty file to anything skimming the summary.
        "conflicts": sum(row["status"] == "conflict" for row in rows),
        "blocked": sum(row["status"] == "blocked" for row in rows),
        "invalid": sum(row["status"] == "invalid" for row in rows),
        "skipped_blank": skipped_blank,
        "skipped_pending": skipped_pending,
        # Accounts a row posts to that the ledger still does not open after
        # this import — duplicates included, whose new text would carry them
        # too — so the frontend never remembers a mistyped `--account` or
        # `--default-account` as a source of this header (w5/452).
        "unopened_accounts": sorted(
            {
                posting.account
                for entry in entries
                if isinstance(entry, Transaction)
                for posting in entry.postings
                if posting.account not in opened_after
            }
        ),
        "validation_errors": validation_errors,
        "validation_warnings": validation_warnings,
        "importer_output": logs.getvalue(),
        "notes": notes,
        "diff": "".join(
            difflib.unified_diff(
                original.decode("utf-8").splitlines(True),
                proposed.splitlines(True),
                fromfile=str(target),
                tofile=str(target),
            )
        ),
    }
    if apply:
        blocked = preview["blocked"]
        if conflicts or (preview["possible_duplicates"] and duplicates == "review") or blocked:
            review = [
                f"Row {row['row']} ({row['status']}): {row['reason']}"
                for row in rows
                if row["status"] == "conflict"
                or (row["status"] == "possible_duplicate" and duplicates == "review")
                or row["status"] == "blocked"
            ]
            fixes = []
            if ledger_conflicts:
                fixes.append(
                    "a stable ID already matches a ledger entry with different data — edit or remove that "
                    "entry, change the bank ID, or drop the row"
                )
            if batch_conflicts:
                fixes.append(
                    "a stable ID repeats within this export with different data — correct or drop one of "
                    "those rows in the source file, or map a different id column"
                )
            if price_conflicts:
                fixes.append(
                    "a price differs from the quote already recorded for that commodity and day — drop the row, "
                    "or record a second quote deliberately with bea add price --force"
                )
            conflict_fix = "; ".join(fixes)
            if conflicts and not (preview["possible_duplicates"] and duplicates == "review"):
                guidance = f"Import needs review; nothing was written. {conflict_fix[:1].upper()}{conflict_fix[1:]}."
            elif conflicts:
                guidance = (
                    f"Import needs review; nothing was written. Resolve ID conflicts ({conflict_fix}) and choose "
                    "--duplicates skip/include for possible duplicates."
                )
            elif preview["possible_duplicates"] and duplicates == "review":
                guidance = (
                    "Import needs review; nothing was written. Choose --duplicates skip/include "
                    "for possible duplicates."
                )
            else:
                guidance = "Import needs review; nothing was written."
            if blocked == 1:
                guidance += " 1 row is blocked by an unopened account or a currency mismatch; resolve it first."
            elif blocked:
                guidance += (
                    f" {blocked} rows are blocked by unopened accounts or currency mismatches; resolve them first."
                )
            raise ConflictError(
                guidance,
                details=review,
                ledger_errors=validation_warnings,
                result=preview,
            )
        if validation_errors:
            raise LedgerError(
                "Import would leave the ledger invalid; nothing was written.",
                details=validation_errors,
                ledger_errors=validation_warnings,
                result=preview,
            )
        snapshot.verify()
        # The preview's validation was of these texts against this snapshot,
        # which `append` verifies unchanged under the lock (w5/577).
        ledger_write.append(
            file,
            texts,
            allow_errors=allow_errors,
            expected=original,
            into=into,
            snapshot=snapshot,
            validated=validation_warnings,
        )
        preview["written"] = len(texts)
    return preview


def _unlocated(lines: list[str]) -> list[str]:
    """Refusal lines without the location of a row that was never written."""
    return [re.sub(r"^Proposed append \(not written\): ", "", line) for line in lines]


def _named_rows(file: Path, texts: list[str], error: LedgerError, *, allow_errors: bool, into: Path | None) -> Any:
    from bea_engine.ledger.adding import _named_rows as named_rows

    return named_rows(file, texts, error, allow_errors=allow_errors, into=into)


def _extracted(importer: Any, source: Path, existing: Any) -> list[Any]:
    """The importer's rows, refusing a return value that is not a list of directives.

    `list()` of a returned string split it into characters, which then failed
    as `'str' object has no attribute '_replace'`, and a returned `None`
    failed as "not iterable" — neither saying what the importer got wrong
    (w5/319).
    """
    from beancount.core.data import ALL_DIRECTIVES

    result = importer.extract(str(source), existing)
    # One directive is a namedtuple, so `list()` took its fields for rows:
    # "row 1 is a dict" (w5/639).
    if result is None or isinstance(result, str | bytes | dict) or isinstance(result, ALL_DIRECTIVES):
        single = "; return [entry] for one" if isinstance(result, ALL_DIRECTIVES) else ""
        raise LedgerError(
            f"Importer {_name(importer)} extract() returned {_type_name(result)} instead of a list of "
            f"Beancount directives{single}."
        )
    return copy.deepcopy(list(result))


def _type_name(value: Any) -> str:
    return "None" if value is None else f"a {type(value).__name__}"


def _writable(entry: Any, row: int, importer: Any, logs: io.StringIO) -> Any:
    """One importer row with integer metadata as numbers, proven printable.

    An importer builds its entries in Python, where `check_number=1042` is an
    `int`; Beancount's printer writes only `Decimal` numbers, so the row failed
    as a bare `ValueError: Unexpected value: '1042'` (w5/227). A non-boolean
    integer is the number it says, as `bea add transactions` already reads it.
    Whatever still cannot be printed — a float, an object, a `custom` whose
    values are plain tuples — is the importer's to fix, so the failure names
    the importer and the row instead of reaching the generic handler.
    """

    def numbers(meta: Any) -> Any:
        if not isinstance(meta, dict):
            return meta
        return {
            key: Decimal(value)
            if isinstance(value, int) and not isinstance(value, bool) and key != "lineno" and not key.startswith("__")
            else value
            for key, value in meta.items()
        }

    import datetime

    from beancount.core.data import ALL_DIRECTIVES, Transaction

    if not isinstance(entry, ALL_DIRECTIVES):
        raise _with_output(
            LedgerError(
                f"Importer {_name(importer)} row {row} is {_type_name(entry)}, not a Beancount directive; "
                "extract() must return a list of directives."
            ),
            logs,
        )
    unwritable = f"Importer {_name(importer)} row {row} cannot be written as a ledger entry"
    # A string or a datetime failed later as a bare AttributeError or
    # TypeError naming no row (w5/638).
    if type(entry.date) is not datetime.date:
        raise _with_output(
            LedgerError(f"{unwritable}: its date is {_type_name(entry.date)} ({entry.date!r}), not a datetime.date."),
            logs,
        )
    try:
        # Accounts as the ledger reads them, NFC: an NFD `Expenses:Café` from a
        # PDF or a macOS file name was "not open", with a duplicate `add open`
        # as the remedy (w5/530).
        entry = nfc_entry_accounts(entry._replace(meta=numbers(entry.meta)))
        if hasattr(entry, "postings"):
            entry = entry._replace(
                postings=[posting._replace(meta=numbers(posting.meta)) for posting in entry.postings]
            )
        text = format_entry(entry) if isinstance(entry, Transaction) else _directive_text(entry)
    except EngineError as exc:
        _with_output(exc, logs)
        raise
    except Exception as exc:
        raise _with_output(
            LedgerError(f"{unwritable} ({type(exc).__name__}): {exc}.", traceback=_traceback(exc)), logs
        ) from exc
    # Printable is not readable: an uppercase metadata key, a NaN amount or a
    # tag with a space prints, then reads back as no directive. The batch
    # check that caught it numbered only the ready rows and stopped the
    # preview with a usage error (w5/638).
    if _invalid_name(entry) is not None:
        # Blocked with `add`'s own words for the name, and never written (w5/637).
        return entry
    if isinstance(entry, Transaction) and "_csv_rule" in entry.meta:
        # The column mapper's note of the rule it applied, taken off before the row is written.
        text = format_entry(entry._replace(meta={k: v for k, v in entry.meta.items() if k != "_csv_rule"}))
    problem = ledger_write.one_entry_problem(text)
    if problem is not None:
        raise _with_output(LedgerError(f"{unwritable}: it {problem}"), logs)
    return entry


def _is_missing_dependency(exc: ImportError, beside: Path) -> bool:
    """Whether `exc` reports a module that cannot be found, rather than a
    module beside the configuration that was imported the wrong way."""
    if not isinstance(exc, ModuleNotFoundError):
        return False
    top = (exc.name or "").partition(".")[0]
    return not top or not ((beside / f"{top}.py").is_file() or (beside / top).is_dir())


def _importer(config: Path, source: Path, name: str | None) -> Any:
    if not config.is_file():
        raise UsageError(f"Importer configuration not found: {config}")
    namespace = runpy.run_path(str(config))
    configured = namespace.get("CONFIG")
    if not isinstance(configured, list | tuple):
        raise UsageError("Importer configuration must export CONFIG = [importer, ...]. See docs/IMPORTING.md.")
    # Two instances of one class share a name, so each also answers to NAME#N,
    # its position among the importers of that name.
    selectors = _selectors(configured)
    chosen = list(zip(selectors, configured, strict=True))
    if name is not None:
        named = [pair for pair in chosen if _name(pair[1]) == name] or [pair for pair in chosen if pair[0] == name]
        if not named:
            raise UsageError(f"No importer named {name!r}; available: {', '.join(selectors) or '(none)'}.")
        chosen = named
    matches = [pair for pair in chosen if pair[1].identify(str(source))]
    if not matches:
        selected = f"Importer {name!r} does not recognize" if name else "No configured importer recognizes"
        raise UsageError(f"{selected} {source.name}. Check --config and the export format.")
    if len(matches) > 1:
        if all(selector == _name(importer) for selector, importer in matches):
            raise UsageError("Multiple importers match; choose one with --importer.", details=[s for s, _ in matches])
        raise UsageError(
            "Multiple importers match and share a name; choose one with --importer NAME#N as listed, "
            "or give each importer a distinct name.",
            details=[_described(selector, importer, source) for selector, importer in matches],
        )
    return matches[0][1]


def _selectors(configured: Sequence[Any]) -> list[str]:
    names = [_name(importer) for importer in configured]
    seen: dict[str, int] = {}
    selectors = []
    for name in names:
        seen[name] = seen.get(name, 0) + 1
        selectors.append(name if names.count(name) == 1 else f"{name}#{seen[name]}")
    return selectors


def _described(selector: str, importer: Any, source: Path) -> str:
    """The selector with the account it files under, which is what tells two
    instances of one class apart."""
    try:
        account = importer.account(str(source))
    except Exception:
        return selector
    return f"{selector} ({account})" if isinstance(account, str) and account else selector


def _name(importer: Any) -> str:
    """The importer's name, or a refusal naming the CONFIG entry and its fix.

    "Use the current Beangulp Importer interface" named neither which entry
    nor what to do, so one legacy importer beside a working one blocked the
    whole configuration without a clue (w5/639).
    """
    if isinstance(importer, type):
        raise UsageError(
            f"CONFIG lists the class {importer.__name__}, not an importer; list an instance, {importer.__name__}(...)."
        )
    kind = type(importer).__name__
    name = getattr(importer, "name", kind)
    if callable(name):
        raise UsageError(
            f"CONFIG entry {kind} is a Beancount v2 importer (its name is a method); wrap it as "
            f"beangulp.Adapter({kind}(...)), or port it to the current Beangulp Importer interface "
            "(a name property and file paths)."
        )
    if not isinstance(name, str):
        raise UsageError(f"CONFIG entry {kind} has a name that is {_type_name(name)}; its name must be a str.")
    return name


def _has_explicit_units(posting: Any) -> bool:
    units = posting.units
    return units is not None and isinstance(getattr(units, "number", None), Decimal)


def _source_legs(entry: Any, account: str) -> list[Any]:
    """The postings of an entry that belong to the importer's source account.

    Beangulp defines `account()` as where the document is filed, so a brokerage
    importer returns one root (`Assets:Broker`) and posts to `Assets:Broker:Cash`
    and `Assets:Broker:HOOL`. Matching the name exactly refused that whole
    batch (w5/223). A posting to the account itself still decides alone when
    there is one, so a row that also moves money to a sub-account keeps the
    source amounts, and the generated id, it always had.
    """
    exact = [p for p in entry.postings if p.account == account]
    return exact or [p for p in entry.postings if p.account.startswith(f"{account}:")]


def _source_postings(entry: Any, account: str) -> list[Any]:
    return [p for p in _source_legs(entry, account) if _has_explicit_units(p)]


_Lot = tuple[Decimal | None, str | None, str | None]


def _lot(posting: Any) -> _Lot | None:
    """The per-unit number, currency and label a source posting's cost states.

    None for a posting held at no cost. A field the cost leaves open is None:
    an importer's `{}` or `{USD}` states less than the ledger's copy of the
    same entry, whose booking filled the rest in. The lot date is left out,
    since booking always fills it in.
    """
    cost = posting.cost
    if cost is None:
        return None
    per = getattr(cost, "number_per", None) if hasattr(cost, "number_per") else getattr(cost, "number", None)
    total = getattr(cost, "number_total", None)
    if not isinstance(per, Decimal) and isinstance(total, Decimal) and isinstance(posting.units.number, Decimal):
        per = total / abs(posting.units.number) if posting.units.number else None
    return (
        per if isinstance(per, Decimal) else None,
        cost.currency if isinstance(cost.currency, str) else None,
        getattr(cost, "label", None) or None,
    )


def _price_text(posting: Any) -> str:
    price = posting.price
    if price is not None and isinstance(price.number, Decimal) and isinstance(price.currency, str):
        return f" @ {_exact_amount(price.number, price.currency)}"
    return ""


def _lot_text(posting: Any) -> str:
    """A source posting's cost or price, as it bears on which source row this is.

    Two same-day buys of `10 AAPL` at 100 and 120 USD are two rows; hashing
    units alone gave them one id, and the second was skipped as an exact
    duplicate with exit 0 (w5/349). A cost is written only when it states
    both its number and currency, so an open `{}` adds nothing.
    """
    lot = _lot(posting)
    cost = ""
    if lot is not None and lot[0] is not None and lot[1] is not None:
        label = f', "{lot[2]}"' if lot[2] else ""
        cost = f" {{{_exact_amount(lot[0], lot[1])}{label}}}"
    return cost + _price_text(posting)


_Leg = tuple[str, _Lot | None]


def _legs(entry: Any, account: str) -> tuple[_Leg, ...]:
    """Each source posting's units and price as text, beside its stated lot."""
    return tuple(
        (_exact_amount(p.units.number, p.units.currency) + _price_text(p), _lot(p))
        for p in _source_postings(entry, account)
    )


def _lots_agree(ours: _Lot | None, theirs: _Lot | None) -> bool:
    if ours is None or theirs is None:
        return ours is theirs
    return all(a is None or b is None or a == b for a, b in zip(ours, theirs, strict=True))


def _legs_agree(ours: Sequence[_Leg], theirs: Sequence[_Leg]) -> bool:
    """Whether two rows move the same source amounts out of the same lots.

    A cost field either side leaves open agrees with any value. An importer
    that sells `-4 HOOL {}` describes the entry the ledger holds as
    `-4 HOOL {150 USD}` once booked, and comparing the two as text made a
    hand-entered twin new and bea's own write a conflict (w5/467). Lots both
    sides state at 100 and 120 USD still differ (w5/349).
    """
    left = list(theirs)
    # A stated lot picks first, so an open one cannot take the leg it needs.
    for text, lot in sorted(ours, key=lambda leg: 0 if leg[1] is None else leg[1].count(None)):
        match = next((i for i, (other, found) in enumerate(left) if other == text and _lots_agree(lot, found)), None)
        picked = [match] if match is not None else _split_booking(text, lot, left)
        if not picked:
            return False
        for index in sorted(picked, reverse=True):
            del left[index]
    return not left


def _units_of(text: str) -> tuple[Decimal, str, str]:
    """A leg's units number, currency and price, from the text `_legs` writes."""
    units, _, price = text.partition(" @ ")
    number, currency = units.split(" ", 1)
    return Decimal(number), currency, price


def _split_booking(text: str, lot: _Lot | None, left: list[_Leg]) -> list[int]:
    """The legs an open-cost leg was booked into, or none.

    Booking reduces as many lots as a `{}` sale spans, so the ledger holds one
    posting per lot where the importer has one: `-20 HOOL {}` was booked as
    `-10 HOOL {150 USD}` and `-10 HOOL {155 USD}`, re-importing bea's own
    write was a conflict, and a hand-entered FIFO twin was written again
    (w5/603). They are the legs of its currency and price whose lots agree
    with what it states, and their units must add up to its own.
    """
    if lot is None or lot[0] is not None:
        return []
    number, currency, price = _units_of(text)
    picked = [
        index
        for index, (other, found) in enumerate(left)
        if found is not None and _units_of(other)[1:] == (currency, price) and _lots_agree(lot, found)
    ]
    if len(picked) < 2 or sum(_units_of(left[index][0])[0] for index in picked) != number:
        return []
    return picked


def _fingerprint(entry: Any, account: str) -> tuple[Any, ...]:
    if any(not _has_explicit_units(p) for p in _source_legs(entry, account)):
        raise LedgerError(f"The importer must supply explicit source amounts for {account} before duplicate matching.")
    # The same rendering the generated id uses, so "is this the same amount"
    # has one answer in this module. `str(number.normalize())` would say
    # `1E+2` where the id says `100`; both sides of a comparison are built the
    # same way, so that was consistent rather than wrong — but two spellings of
    # one rule is how they drift apart. The legs compare with `_legs_agree`,
    # never `==`, so an open cost matches the lot booking chose.
    # Ledger text loads NFC-normalized but an export's rows arrive in whatever
    # form the bank wrote, so an accented description would otherwise compare
    # unequal to the identical entry already in the ledger.
    return (
        entry.date,
        _match_text(entry.payee),
        _match_text(entry.narration),
        _legs(entry, account),
    )


def _written_quotes(existing: Sequence[Any]) -> dict[tuple[Any, str, str], list[Any]]:
    """The ledger's own price directives by day and pair, as `add price` counts them.

    A price a plugin such as `implicit_prices` generates, or one from the
    managed quote cache, is no quote the ledger records.
    """
    from beancount.core.data import Price

    from bea_engine.ledger.reader import entry_generated
    from bea_engine.managed_price_cache import managed_source_for_path

    quotes: dict[tuple[Any, str, str], list[Any]] = {}
    for entry in existing:
        if not isinstance(entry, Price) or entry_generated(entry, "price"):
            continue
        filename = entry.meta.get("filename")
        if isinstance(filename, str) and filename and managed_source_for_path(Path(filename)) is not None:
            continue
        quotes.setdefault((entry.date, entry.currency, entry.amount.currency), []).append(entry)
    return quotes


def _quote_origin(quote: Any, batch_rows: dict[int, int]) -> str:
    row = batch_rows.get(id(quote))
    if row is not None:
        return f"row {row} of this import"
    return f"{quote.meta.get('filename')}:{quote.meta.get('lineno')}"


def _plain_amount(amount: Any) -> str:
    return f"{format(amount.number, 'f')} {amount.currency}"


def _directive_text(entry: Any) -> str:
    """A non-transaction directive as it prints once it is in the ledger.

    This text is both what is appended and what "identical directive" compares,
    so it has to survive a reload unchanged. The loader reads ledger text as
    NFC, and a balance that currently fails loads with its computed difference
    attached, which the printer would append as a `; Diff:` comment (w5/224).
    """
    if getattr(entry, "diff_amount", None) is not None:
        entry = entry._replace(diff_amount=None)
    return unicodedata.normalize("NFC", format_entry(entry))


def _match_text(value: str | None) -> str:
    return unicodedata.normalize("NFC", " ".join((value or "").casefold().split()))


def _identities(entry: Any, account: str, keys: list[str]) -> list[tuple[str, str, str]]:
    meta = entry.meta or {}
    identities = []
    for key in ["import-id", *keys]:
        value = meta.get(key)
        if value in (None, ""):
            continue
        if key == "import-id":
            identities.append((account, "import-id", str(value)))
        else:
            identities.append((account, "bank", f"{_IDENTITY_KINDS.get(key, key)}:{value}"))
    if meta.get("import-id-2") not in (None, ""):
        identities.append((account, "import-id", str(meta["import-id-2"])))
    if meta.get("bea_import_id"):
        identities.append((account, "file", str(meta["bea_import_id"])))
    # beancount-migrate writes the same digest under its source's prefix
    # (`monarch:sha256:…`), so a later bank import of that row must find it.
    for value in (meta.get("import-id"), meta.get("import-id-2")):
        if (match := _GENERATED_ID.fullmatch(str(value or ""))) is not None:
            identities.append((account, "digest", match.group(1)))
    return identities


# The generated ids skills/.../beancount-import/references/dedup.md defines:
# `bea import` writes `csv:`, beancount-migrate `mint:`/`monarch:`/`qbo:`, and
# `<source>:` for any other source (`ynab:`, `actual:`). Listing four missed
# the generic path, and every overlap row after such a migration was written
# again (w5/601).
_GENERATED_ID = re.compile(r"[a-z][a-z0-9-]*:sha256:([0-9a-f]{16})")


def _is_generated_identity(key: tuple[str, str, str]) -> bool:
    return key[1] == "digest" or (key[1] == "import-id" and _GENERATED_ID.fullmatch(key[2]) is not None)


def _twin_reason(entry: Any, twin: Any, earlier: int | None, *, ours: bool, keys: list[str]) -> str:
    """Why a row may repeat `twin`, naming only the bank IDs that exist.

    Two same-day charges with no ID column read "different bank IDs do not
    rule out a duplicate", about IDs neither row had (w5/615).
    """
    theirs = _native_import_id(twin.meta or {}, keys) is not None or (
        bool(twin.meta.get("import-id")) and _GENERATED_ID.fullmatch(str(twin.meta["import-id"])) is None
    )
    if ours and theirs:
        ids = "their bank IDs differ, which does not rule out a duplicate"
    elif ours or theirs:
        ids = "only one of them carries a bank ID"
    else:
        ids = "neither row has a bank ID" if earlier is not None else "neither has a bank ID"
    named = "payee" if _match_text(entry.payee) else "narration"
    where = f" row {earlier} of this import" if earlier is not None else ""
    return f"Date, {named} and source amount match{where}; {ids}."


def _is_native_identity(key: tuple[str, str, str]) -> bool:
    """A bank's or importer's own id, unique only within the account that issued it."""
    return key[1] in {"bank", "import-id"} and not _is_generated_identity(key)


#: How far apart the two sides of one transfer may post and still read as one.
_TRANSFER_DAYS = 7

#: How far a ledger entry's date may sit from its row's under one bank id and
#: still be that row with its date corrected, rather than the id reused (w5/599).
_REUSED_REFERENCE_DAYS = 7


def _nearest(entries: list[Any], entry: Any, account: str, fingerprint: tuple[Any, ...]) -> Any:
    """Of the entries under one bank id, the one with this row's source amounts dated nearest it."""
    agreeing = [found for found in entries if _legs_agree(fingerprint[3], _fingerprint(found, account)[3])]
    return min(agreeing or entries, key=lambda found: abs((entry.date - found.date).days))


def _issued_elsewhere(entry: Any, account: str, balance_roots: tuple[str, ...]) -> bool:
    """Whether another account issued the native ids of an entry that posts to `account`.

    bea writes the source posting first, so an entry whose first posting is
    another balance-sheet account is that account's import, a transfer, and
    its bank id is scoped there: checking's `1001` deduped savings' own
    `1001`, a different deposit, as an exact duplicate (w5/598). An income or
    expense leg first is no such evidence: some importers list it first.
    """
    first = entry.postings[0] if entry.postings else None
    if first is None or any(first is leg for leg in _source_legs(entry, account)):
        return False
    return first.account.split(":", 1)[0] in balance_roots


def _transfer_side(
    ids: list[tuple[str, str, str]],
    transfer_ids: dict[tuple[str, str, str], Any],
    entry: Any,
    account: str,
    fingerprint: tuple[Any, ...],
) -> tuple[tuple[str, str, str], Any] | None:
    """A transfer whose other side may be this row: its issuer's id, the same amount here, days apart at most.

    Some banks give both legs of a transfer one reference, so the id is kept
    as evidence, but only for review: the same id on another date or amount
    is another transaction.
    """
    for key in ids:
        found = transfer_ids.get(key)
        if (
            found is not None
            and abs((found.date - entry.date).days) <= _TRANSFER_DAYS
            and _legs_agree(fingerprint[3], _fingerprint(found, account)[3])
        ):
            return key, found
    return None


#: How far apart two banks may date one transfer's sides when only the amount pairs them.
_COUNTERPART_DAYS = 3


def _amounts_key(fingerprint: tuple[Any, ...]) -> tuple[str, ...]:
    """The source amounts, summed by currency and price: one sale booked across lots is one amount (w5/603)."""
    totals: dict[tuple[str, str], Decimal] = {}
    for text, _ in fingerprint[3]:
        number, currency, price = _units_of(text)
        totals[currency, price] = totals.get((currency, price), Decimal(0)) + number
    return tuple(
        sorted(
            f"{_exact_amount(number, currency)}{f' @ {price}' if price else ''}"
            for (currency, price), number in totals.items()
        )
    )


def _transfer_counterpart(
    counterparts: dict[tuple[str, ...], list[Any]], entry: Any, account: str, fingerprint: tuple[Any, ...]
) -> Any:
    """A transfer another account's import wrote that posts this row's amount here, days apart at most.

    "TRANSFER TO SAVINGS" and "TRANSFER FROM CHECKING" share no word, so the
    second side of every transfer imported from both banks was booked again
    with exit 0 (w5/600). For review only: the same amount near the same day
    can be a separate payment.
    """
    return next(
        (
            found
            for found in reversed(counterparts.get(_amounts_key(fingerprint), []))
            if abs((found.date - entry.date).days) <= _COUNTERPART_DAYS
            and _legs_agree(fingerprint[3], _fingerprint(found, account)[3])
        ),
        None,
    )


def _relative_days(written: Any, row: Any) -> str:
    days = (row - written).days
    if days == 0:
        return "the same day"
    return f"{abs(days)} day{'s' if abs(days) != 1 else ''} {'earlier' if days > 0 else 'later'}"


def _same_row(
    key: tuple[str, str, str], found: Any, account: str, fingerprint: tuple[Any, ...], *, lookup_only: bool
) -> bool:
    """Whether an id hit names the same source row rather than changed data.

    Canonical hashes already identify the original source row; mutable ledger
    fields cannot invalidate that proof. Older lookup-only hashes retain the
    date/amount guard against lossy collisions. Native IDs compare exact source
    amounts and commodities, allowing date and description cleanup. Pre-release
    file identities retain their full-content comparison.
    """
    generated = _is_generated_identity(key)
    if generated and not lookup_only:
        return True
    found_print = _fingerprint(found, account)
    if not _legs_agree(fingerprint[3], found_print[3]):
        return False
    if generated:
        return bool(found_print[0] == fingerprint[0])
    if key[1] in {"bank", "import-id"}:
        return True
    return found_print[:3] == fingerprint[:3]


def _valid_account(name: str, option: str, roots: tuple[str, ...]) -> str:
    """Validate an account name the way the loader will, saying which option named it.

    Import used to skip this check entirely. An unopenable name — a space, a
    lowercase root, an illegal character — is trivially absent from the set of
    opened accounts, so every row came back `blocked` with "is not open" and a
    `bea add open` remedy that `add` itself refuses. A name no `open` directive
    could ever make valid is a usage error, not an unopened account, and this
    is the validator `add` has always used for it.
    """
    from bea_engine.ledger.text import parse_account

    try:
        return parse_account(name, roots)
    except UsageError as exc:
        raise UsageError(f"{option}: {exc}") from None


def _row_currency(existing: list[Any], account: str, options: Any, *, checked: bool = True) -> str | None:
    """The commodity an imported row posts when no currency column names one.

    The source account decides before the ledger does: an account opened for a
    single currency *is* the commodity its statement is denominated in, and
    reaching for the ledger's single `operating_currency` instead booked every
    euro line of a euro account as dollars — exit 0, green `bea check`, wrong
    money. The operating currency stays the fallback for an account opened for
    any commodity; `None` leaves the row to the currency column or a refusal.
    """
    from beancount.core.data import Open

    opened: set[str] | None = set()
    for entry in existing:
        if isinstance(entry, Open) and entry.account == account:
            if not entry.currencies:
                opened = None
                break
            opened = (opened or set()) | set(entry.currencies)
    if opened is not None and len(opened) == 1:
        return next(iter(opened))
    # Checked only when nothing else can name the row's commodity: a mapped
    # currency column makes this fallback one no row may need.
    operating = checked_operating_currencies(options) if checked else list(options.get("operating_currency") or ())
    return operating[0] if len(operating) == 1 else None


def _known_currencies(existing: list[Any], operating: list[str]) -> frozenset[str]:
    """Commodities the ledger names: declared, opened for, posted, priced, or operating."""
    from beancount.core.data import Commodity, Open, Price, Transaction

    known = set(operating)
    for entry in existing:
        if isinstance(entry, Commodity):
            known.add(entry.currency)
        elif isinstance(entry, Open):
            known.update(entry.currencies or ())
        elif isinstance(entry, Price):
            known.update((entry.currency, entry.amount.currency))
        elif isinstance(entry, Transaction):
            known.update(posting.units.currency for posting in entry.postings if posting.units is not None)
    return frozenset(currency for currency in known if isinstance(currency, str))


def _posting_currency(posting: Any, entry: Any) -> str | None:
    """The currency a posting carries, or the one Beancount will infer for an amountless leg.

    An importer may leave the categorized leg without an amount. Interpolation
    fills it with the balancing weight, so its currency is the single weight
    currency of the other legs; with several, it cannot be told before booking.
    """
    if posting.units is not None:
        return str(posting.units.currency)
    weights = set()
    for other in entry.postings:
        if other.units is None:
            continue
        if other.cost is not None and getattr(other.cost, "currency", None):
            weights.add(other.cost.currency)
        elif other.price is not None:
            weights.add(other.price.currency)
        else:
            weights.add(other.units.currency)
    return str(next(iter(weights))) if len(weights) == 1 else None


def _open_currencies(entries: list[Any], open_type: Any) -> dict[str, set[str] | None]:
    """Per opened account, the currencies its `open` directives allow; None for any."""
    opened: dict[str, set[str] | None] = {}
    for entry in entries:
        if not isinstance(entry, open_type):
            continue
        entry = normalize_entry_strings(entry)
        if not entry.currencies:
            opened[entry.account] = None
        else:
            previous = opened.get(entry.account, set())
            if previous is not None:
                opened[entry.account] = previous | set(entry.currencies)
    return opened


def _active_windows(entries: list[Any]) -> dict[str, tuple[Any, Any]]:
    """Each account's `open` and, if any, `close`: the dates a posting to it is valid."""
    from beancount.core.data import Close, Open

    windows: dict[str, tuple[Any, Any]] = {}
    for entry in entries:
        if isinstance(entry, Open) and entry.account not in windows:
            windows[normalize_entry_strings(entry).account] = (entry, None)
        elif isinstance(entry, Close):
            account = normalize_entry_strings(entry).account
            if account in windows:
                windows[account] = (windows[account][0], entry)
    return windows


_IMPORT_ROW = "__bea_import_row__"
"""Meta key on a reloaded directive the import's own rows wrote: that row's number."""


def _entries_after(
    snapshot: ledger_write.LedgerSnapshot, target: Path, original: bytes, texts: list[str], rows: list[int]
) -> list[Any]:
    """The ledger's entries with `texts` (rows `rows`) appended, plugins applied; nothing is written.

    Errors are not this load's business: an account nothing opens is simply
    absent from the result, and the append is validated on its own afterwards.

    Each entry names its real file, and one the appended rows wrote names its
    row: a blocked row's reason cited the open as `.bea-<hex>.tmp:9`, a
    staging file gone when the command returned (w5/636).
    """
    from bea_engine import managed_load

    ledger_write.refuse_cache_over_ledger(target, snapshot.contents, snapshot.patterns)
    with ledger_write.candidate_file(target, ledger_write.decoded_append(target, original, texts)) as candidate:
        with snapshot.staged(candidate, target) as (root, staged):
            entries, _, _ = managed_load.load_file(root)
    back = {str(copy): str(source) for copy, source in staged.items()}
    spans = list(zip(ledger_write.appended_spans(original, texts), rows, strict=True))
    written = os.path.normpath(target)
    result = []
    for entry in entries:
        entry = managed_load._remap_entry(entry, back)
        meta = getattr(entry, "meta", None) or {}
        if os.path.normpath(str(meta.get("filename"))) == written and isinstance(meta.get("lineno"), int):
            row = next((row for (first, last), row in spans if first <= meta["lineno"] <= last), None)
            if row is not None:
                entry = entry._replace(meta={**meta, _IMPORT_ROW: row})
        result.append(entry)
    return result


def _entry_accounts(entry: Any, *, active_only: bool = False) -> list[tuple[str, str | None]]:
    """Each account an imported directive needs open, with the currency it puts there when known.

    Only transactions were checked, so an importer's closing `balance` or a
    `note` on a never-opened account was counted ready and then failed the
    whole `--apply` with exit 1 (w5/351). A note or document may follow a
    close, as Beancount allows, so `active_only` leaves them out.
    """
    from beancount.core.data import Balance, Close, Document, Note, Pad, Transaction

    if isinstance(entry, Transaction):
        return [(posting.account, _posting_currency(posting, entry)) for posting in entry.postings]
    if isinstance(entry, Balance):
        return [(entry.account, entry.amount.currency)]
    if isinstance(entry, Pad):
        return [(entry.account, None), (entry.source_account, None)]
    if isinstance(entry, Close):
        return [(entry.account, None)]
    if isinstance(entry, Note | Document) and not active_only:
        return [(entry.account, None)]
    return []


def _first_uses(entries: list[Any], transaction: Any) -> dict[str, tuple[Any, list[str] | None]]:
    """Per account, the earliest date any row of this import posts to it, and the currencies posted.

    A blocked row's `add open` remedy has to fix the import it was printed
    for. Dated per row, the first suggestion of a newest-first export opened
    the account after the older rows, and the retry failed on an inactive
    account that only a hand edit could clear (w5/076). The currencies are
    None when any posting's cannot be told before booking.
    """
    uses: dict[str, tuple[Any, list[str] | None]] = {}
    for entry in entries:
        posts = isinstance(entry, transaction)
        for name, currency in _entry_accounts(entry):
            date, currencies = uses.get(name, (entry.date, []))
            # Only a posting's unknown currency leaves the constraint open; a
            # note or document names no currency at all.
            if posts and (currency is None or currencies is None):
                currencies = None
            elif currency is not None and currencies is not None and currency not in currencies:
                currencies = [*currencies, currency]
            uses[name] = (min(date, entry.date), currencies)
    return uses


def _blocked_reason(
    entry: Any,
    open_currencies: dict[str, set[str] | None],
    roots: tuple[str, ...],
    first_uses: dict[str, tuple[Any, list[str] | None]],
    stage_opens: bool = False,
    *,
    ledger: Path,
    source: str | None = None,
    windows: dict[str, tuple[Any, Any]] | None = None,
) -> str | None:
    """Why a transaction cannot be written, or None when its accounts allow it.

    Names each unopened account with the `bea add open` line that fixes it,
    and each currency the account's open directive does not allow. The line is
    one command per account, dated and constrained for every row of the import
    that posts there. `stage_opens` is a ledger loading `nounused`, where the
    open is refused until used unless staged with `--allow-errors`. An account
    under a root the ledger does not use (from a Python importer) gets no
    `add open` remedy: that command would refuse it too.
    """
    invalid = _invalid_name(entry)
    if invalid is not None:
        chose = (
            "Correct the rule, category column or --default-account that chose it."
            if source is not None
            else "The importer has to return a valid one."
        )
        return f"{invalid.rstrip('.')}. {chose}"
    referenced = _entry_accounts(entry)
    missing = sorted({name for name, _ in referenced if name not in open_currencies})
    foreign = [name for name in missing if name.split(":", 1)[0] not in roots]
    if foreign:
        return unknown_root_message(foreign[0], roots)
    if missing:
        remedies = []
        flag = " --allow-errors" if stage_opens else ""
        bea = bea_command(ledger)
        for name in missing:
            opened, currencies = first_uses.get(name, (entry.date, None))
            # Quoted so the line survives a paste into a shell. Valid account
            # names hold no spaces, so this is belt-and-braces now that invalid
            # names are refused up front — but a suggestion that only sometimes
            # pastes cleanly is worse than one that always does.
            constraint = "".join(f" -c {currency}" for currency in sorted(currencies or ()))
            remedies.append(
                f"{bea} add open --account {shlex.quote(name)} --date {opened.isoformat()}{constraint}{flag}"
            )
        quoted = ", ".join(f"'{name}'" for name in missing)
        noun = "Account" if len(missing) == 1 else "Accounts"
        verb = "is" if len(missing) == 1 else "are"
        return f"{noun} {quoted} {verb} not open. Run: {'; '.join(remedies)}."
    inactive = _inactive_reason(entry, windows or {}, first_uses, source)
    if inactive is not None:
        return inactive
    for name, currency in referenced:
        allowed = open_currencies.get(name)
        # A currency that cannot be told before booking is validation's to judge.
        if allowed is not None and currency is not None and currency not in allowed:
            choices = ", ".join(sorted(allowed))
            instead = choices if len(allowed) == 1 else f"one of {choices}"
            # Widening the open directive is the last remedy offered, not the
            # first: following it relabels foreign money as the wrong commodity.
            # `currency=` sets every posting's commodity, so it is the fix only
            # on a CSV run's source account; a Python importer cannot take
            # `--csv` at all, and on a category account it moved the block to
            # the source account (w5/318).
            blocked = f"Cannot post {currency} to '{name}' (open for {choices} only)."
            widen = f"or add {currency} to its open directive"
            if source is not None and name == source:
                return (
                    f"{blocked} Post {instead} instead — name the row's commodity with --csv currency=CODE — {widen}."
                )
            if source is not None:
                return (
                    f"{blocked} Book the row to an account open for {currency} — change the rule, category "
                    f"column or --default-account that chose '{name}' — {widen}."
                )
            return (
                f"{blocked} The importer posts {currency} there: have it post {instead}, or book the row "
                f"to an account open for {currency} — {widen}."
            )
    return None


def _invalid_name(entry: Any) -> str | None:
    """`add`'s refusal for the first account or commodity no ledger can hold, or None.

    Only membership in the ledger's opens was asked, so an importer's
    `Expenses:food stuff` or `usd` was "not open", with an `add open` or
    widen-the-open remedy that `add` refuses (w5/637, the importer side of
    w3/386). These are the validators `add` uses.
    """
    from beancount.core.data import Balance, Transaction

    from bea_engine.ledger.text import parse_account, require_commodity

    for name, _ in _entry_accounts(entry):
        try:
            parse_account(name)
        except UsageError as exc:
            return str(exc)
    currencies: list[Any] = []
    if isinstance(entry, Transaction):
        for posting in entry.postings:
            currencies += [getattr(value, "currency", None) for value in (posting.units, posting.cost, posting.price)]
    elif isinstance(entry, Balance):
        currencies.append(entry.amount.currency)
    for currency in currencies:
        if isinstance(currency, str):
            try:
                require_commodity(currency)
            except ValueError as exc:
                return str(exc)
    return None


def _inactive_reason(
    entry: Any,
    windows: dict[str, tuple[Any, Any]],
    first_uses: dict[str, tuple[Any, list[str] | None]],
    source: str | None,
) -> str | None:
    """Why a posting's account cannot take this row's date, though it is opened.

    Only "is there an `open`" was asked, so a rule account closed before the
    row, or opened after it, previewed the row as ready and then failed the
    whole `--apply` with exit 1, valid rows and all (w5/339).
    """
    for name, _ in _entry_accounts(entry, active_only=True):
        window = windows.get(name)
        if window is None:
            continue
        opened, closed = window
        if entry.date < opened.date:
            earliest = first_uses.get(name, (entry.date, None))[0]
            return (
                f"Account '{name}' opens {opened.date} ({_where(opened)}), after this row's "
                f"{entry.date}. Re-date that open to {min(earliest, entry.date)} or earlier."
            )
        if closed is not None and entry.date > closed.date:
            remedy = (
                "Re-date the close, or import into an account that is still open."
                if name == source
                else "Point the rule, category or --default-account at an open account, or re-date the close."
            )
            return (
                f"Account '{name}' was closed {closed.date} ({_where(closed)}), before this row's "
                f"{entry.date}. {remedy}"
            )
    return None


def _where(directive: Any) -> str:
    row = directive.meta.get(_IMPORT_ROW)
    if row is not None:
        return f"row {row} of this import"
    return f"at {directive.meta.get('filename')}:{directive.meta.get('lineno')}"


def _native_import_id(meta: dict[str, Any], keys: list[str]) -> str | None:
    for key in keys:
        value = meta.get(key)
        if value not in (None, ""):
            return f"{_IDENTITY_KINDS.get(key, key)}:{value}"
    return None


def _exact_amount(number: Decimal, currency: str) -> str:
    """One source amount, rendered so equal values render identically.

    `normalize()` collapses the spellings of one value — `1.50`, `1.5` and
    `1.500` are the same amount and must hash the same — and `:f` keeps the
    result out of scientific notation, which `normalize()` otherwise produces
    for trailing zeros before the point (`100` becomes `1E+2`).

    It normalizes under a context as precise as the number itself. The
    default context keeps 28 significant digits, so `1.00…001` and
    `1.00…002` (29+ digits, written exactly to the ledger) rounded to one
    rendering, shared an id, and the second row was skipped as a duplicate.

    The currency is part of the identity. Without it, `1 ETH` and `1 BTC` on
    one date with one description shared a digest.
    """
    return f"{_exactly_normalized(number):f} {currency}"


def _exactly_normalized(number: Decimal) -> Decimal:
    """`number.normalize()` without rounding to the ambient context's precision."""
    return number.normalize(Context(prec=max(len(number.as_tuple().digits), 1)))


def _amounts_rounded(amounts: list[tuple[Decimal, str]]) -> str:
    """The exact-amount rendering as written before it stopped rounding to 28 digits."""
    return "+".join(f"{number.normalize():f} {currency}" for number, currency in amounts)


def _amounts_exact(amounts: list[tuple[Decimal, str]]) -> str:
    """The current rendering: every source amount, exact, with its commodity."""
    return "+".join(_exact_amount(number, currency) for number, currency in amounts)


def _amounts_two_decimal(amounts: list[tuple[Decimal, str]]) -> str:
    """The pre-exactness rendering, kept only to recognize ids already written.

    A lone amount was printed to two decimals with no commodity at all, so
    `-0.001 ETH` and `-0.002 ETH` both became `-0.00` and reordering an export
    swapped which row owned which digest.
    """
    if len(amounts) == 1:
        return f"{amounts[0][0]:.2f}"
    return "+".join(f"{number} {currency}" for number, currency in amounts)


def _hash_base(date: str, amount: str, description: str, account: str) -> str:
    """The string a generated import id is the digest of."""
    return f"{date}|{amount}|{description}|{account}"


def _digest_import_id(base: str, occurrence: int) -> str:
    digest_input = base if occurrence == 1 else f"{base}|{occurrence}"
    return "csv:sha256:" + hashlib.sha256(digest_input.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class _HashedRow:
    """One hashed row's generated ids.

    `canonical` is written. `narration_only` are the ids that may already be
    stored for the row under the narration-only base (`group`): the canonical
    id itself for a row with one description, and every older spelling. Older
    spellings numbered occurrences over every row sharing that base, so which
    stored id belongs to which row is settled for the whole group by
    `_claim_payeeless_ids`, not by row order.
    """

    canonical: str
    group: str
    narration_only: tuple[str, ...]
    payee: str
    date: Any
    legs: tuple[_Leg, ...]


def _hash_rows(entries: list[Any], account: str, keys: list[str], transaction: type[Any]) -> dict[int, _HashedRow]:
    """Generated ids for every row that gets one, numbered in export order.

    The decision mirrors the preview loop: a transaction posting to the source
    account with neither an importer-supplied `import-id` nor a native bank id.
    Hashing ahead of the loop lets a group of rows claim stored ids together.
    """
    seen: dict[str, int] = {}
    hashed: dict[int, _HashedRow] = {}
    for index, raw in enumerate(entries):
        entry = normalize_entry_strings(raw)
        if not isinstance(entry, transaction) or not _source_legs(entry, account):
            continue
        if entry.meta.get("import-id") or _native_import_id(entry.meta, keys) is not None:
            continue
        hashed[index] = _hash_import_ids(entry, account, seen)
    return hashed


def _claim_payeeless_ids(
    hashed: dict[int, _HashedRow], identities: dict[tuple[str, str, str], Any], account: str
) -> tuple[dict[int, list[str]], dict[int, int]]:
    """Give each stored narration-only id to the row it was written for.

    Ids written before payees were hashed number identical narrations in
    export order, so with a reordered export occurrence K is a different row:
    `PEETS` then `STARBUCKS`, both `CARD PURCHASE -5.00`, would have `PEETS`
    match the id stored for `STARBUCKS`. Every stored entry any row of a group
    reaches is therefore claimed by a row of the group with that entry's payee
    first — the row that reached it when that is one, so a row keeps the entry
    its own id names. An entry with no payee goes to a row with no payee the
    same way, never to a payee-bearing row that merely shares its narration.
    An entry whose payee no row has (edited later) keeps the meaning the old
    id had — the row at its occurrence — or, if that row was claimed, the next
    unclaimed row in export order. A row left without a claim has no older id
    at all.

    Returns each row's claimed older ids, and the claiming row of every stored
    entry by `id()`: no other row of the batch may match that entry through a
    generated id.
    """
    groups: dict[str, list[int]] = {}
    for index, row in hashed.items():
        groups.setdefault(row.group, []).append(index)
    claimed: dict[int, list[str]] = {}
    owners: dict[int, int] = {}
    for indices in groups.values():
        stored: list[tuple[Any, str, int]] = []
        # A row's own id reaches first, so an older spelling — numbered
        # differently — cannot take an entry from the row it is canonical for.
        for own in (True, False):
            for index in indices:
                row = hashed[index]
                for value in row.narration_only:
                    if (value == row.canonical) is not own:
                        continue
                    digest = value.rsplit(":", 1)[1]
                    found = identities.get((account, "import-id", value)) or identities.get((account, "digest", digest))
                    if found is None or any(found is entry for entry, _, _ in stored):
                        continue
                    found_print = _fingerprint(found, account)
                    if found_print[0] == row.date and _legs_agree(row.legs, found_print[3]):
                        stored.append((found, value, index))
        unclaimed = list(indices)
        leftover: list[tuple[Any, str, int]] = []
        for legacy in (False, True):
            for found, value, reached_by in leftover if legacy else stored:
                payee = _match_text(found.payee)
                candidates = unclaimed if legacy else [index for index in unclaimed if hashed[index].payee == payee]
                if not candidates:
                    if not legacy:
                        leftover.append((found, value, reached_by))
                    continue
                owner = reached_by if reached_by in candidates else candidates[0]
                unclaimed.remove(owner)
                owners[id(found)] = owner
                if value != hashed[owner].canonical:
                    claimed[owner] = [value]
    return claimed, owners


def _hash_import_ids(entry: Any, account: str, seen: dict[str, int]) -> _HashedRow:
    """The canonical import id, plus every older spelling to also match on.

    The canonical digest hashes the exact amount with its commodity, and hashes
    the description NFC-normalized, so one bank row keeps one id across exports
    that differ only in Unicode normalization or in how many decimal places
    they print.

    Older releases wrote different digests, so those are returned alongside as
    lookup-only keys and no re-hash pass is needed. They are listed newest
    first, and only formats that a released `bea` actually wrote are listed:
    NFC normalization shipped before exact amounts, so a ledger may predate
    exactness, or predate both, but there is no exact-amount/un-normalized
    combination in the wild to look for.

    Older spellings stay numbered over every row sharing the narration-only
    base, as the releases that wrote them numbered it: the older spelling of
    the K-th such row is that format's digest at occurrence K.

    A row with both a payee and a narration hashes both
    (`date|amount|payee|narration|account`): `STARBUCKS / CARD PURCHASE` and
    `PEETS / CARD PURCHASE` are different rows, and the occurrence suffix is
    only for identical ones. A row with one description is numbered among the
    one-description rows alone, so a payee-bearing row ahead of it in the
    export does not change its id. Either way the narration-only spellings are
    returned for the group-wide claim instead of as plain lookups.
    """
    legs = sorted((p.units.number, p.units.currency, _lot_text(p)) for p in _source_postings(entry, account))
    amounts = [(number, currency) for number, currency, _ in legs]
    raw_description = " ".join(str(entry.narration or entry.payee or "").upper().split())
    # Normalize after upper(): uppercasing NFD text can itself emit a
    # non-canonical form, and the digest has to be stable byte-for-byte.
    description = unicodedata.normalize("NFC", raw_description)
    nfc_account = unicodedata.normalize("NFC", account)
    date = entry.date.isoformat()
    units_only = _amounts_exact(amounts)
    exact = "+".join(_exact_amount(number, currency) + lot for number, currency, lot in legs)

    single_base = _hash_base(date, exact, description, nfc_account)
    seen[single_base] = seen.get(single_base, 0) + 1
    occurrence = seen[single_base]

    two_decimal = _amounts_two_decimal(amounts)
    known = {single_base}
    older: list[str] = []
    rounded_base = _hash_base(date, _amounts_rounded(amounts), description, nfc_account)
    if rounded_base != single_base:
        # Amounts past 28 significant digits were hashed rounded, and those
        # rows were numbered among every row rounding to the same base.
        counter = f"rounded\0{rounded_base}"
        seen[counter] = seen.get(counter, 0) + 1
        known.add(rounded_base)
        older.append(_digest_import_id(rounded_base, seen[counter]))
    for base in (
        _hash_base(date, two_decimal, description, nfc_account),  # before exact amounts
        _hash_base(date, two_decimal, raw_description, account),  # and before NFC
    ):
        if base in known:
            continue
        known.add(base)
        older.append(_digest_import_id(base, occurrence))
    if exact != units_only:
        # Written before a lot or price was part of the id: lookup-only, and
        # content-checked like every older spelling, so it matches the same
        # lot and never a different one.
        units_base = _hash_base(date, units_only, description, nfc_account)
        counter = f"units\0{units_base}"
        seen[counter] = seen.get(counter, 0) + 1
        older.append(_digest_import_id(units_base, seen[counter]))
    single = _digest_import_id(single_base, occurrence)

    payee = unicodedata.normalize("NFC", " ".join(str(entry.payee or "").upper().split()))
    if payee and str(entry.narration or "").strip():
        base = _hash_base(date, exact, f"{payee}|{description}", nfc_account)
        # Keyed apart from the narration-only counter, so a paired base can never
        # share an occurrence count with a narration that happens to contain `|`.
        counter = f"paired\0{base}"
        if exact != units_only:
            units_paired = _hash_base(date, units_only, f"{payee}|{description}", nfc_account)
            units_counter = f"paired-units\0{units_paired}"
            seen[units_counter] = seen.get(units_counter, 0) + 1
            older.append(_digest_import_id(units_paired, seen[units_counter]))
    else:
        # Numbered apart from payee-bearing rows. Releases that counted those
        # too wrote `single`, which stays one of the spellings to look for.
        base, counter = single_base, f"single\0{single_base}"
    seen[counter] = seen.get(counter, 0) + 1
    canonical = _digest_import_id(base, seen[counter])
    return _HashedRow(
        canonical=canonical,
        group=single_base,
        narration_only=tuple(dict.fromkeys([*([canonical] if base == single_base else []), single, *older])),
        payee=_match_text(entry.payee),
        date=entry.date,
        # The fingerprint's legs, lot included, so a claim's content check
        # compares like with like (w5/349).
        legs=_legs(entry, account),
    )


def _candidate_key(entry: Any, account: str) -> tuple[Any, ...]:
    """Date, who was paid, and source amounts: what may flag a possible duplicate.

    The amounts leave lots out; `_possible_twin` compares those. The payee
    names who was paid. A row with no payee — the documented
    one-description CSV mapping puts the bank text in `narration` — is named
    by its narration instead; otherwise every same-day same-amount row would
    collapse onto date + amount and `--duplicates skip` would drop real ones.
    """
    fingerprint = _fingerprint(entry, account)
    return fingerprint[0], fingerprint[1] or fingerprint[2], _amounts_key(fingerprint)


def _narration_key(entry: Any, account: str) -> tuple[Any, ...]:
    fingerprint = _fingerprint(entry, account)
    return "narration", fingerprint[0], fingerprint[2], _amounts_key(fingerprint)


def _index_twin(fingerprints: dict[tuple[Any, ...], list[Any]], entry: Any, account: str, *, ledger: bool) -> None:
    """File an entry under who was paid, and a ledger entry also under its narration.

    Rows of one export that differ in whether they name a payee are rows the
    bank listed apart (w5/140), so only the ledger's entries meet across it.
    """
    fingerprints.setdefault(_candidate_key(entry, account), []).append(entry)
    if ledger:
        fingerprints.setdefault(_narration_key(entry, account), []).append(entry)


def _possible_twin(
    fingerprints: dict[tuple[Any, ...], list[Any]],
    entry: Any,
    account: str,
    fingerprint: tuple[Any, ...],
    owners: dict[int, int],
    index: int,
) -> Any:
    """The latest entry sharing the row's candidate key whose lots agree with it, if any.

    Payee meets payee. When either side names none, narration meets
    narration: an entry keyed by its payee never met a one-description row
    of the same text, so a bank export of rows beancount-migrate had written
    as payee + statement text was booked again (w5/602). An entry another
    row of this import owns by its id is that row's, not this one's twin.
    """
    by_narration = [
        found
        for found in fingerprints.get(_narration_key(entry, account), [])
        if owners.get(id(found), index) == index and (not fingerprint[1] or not _match_text(found.payee))
    ]
    candidates = [*reversed(fingerprints.get(_candidate_key(entry, account), [])), *reversed(by_narration)]
    return next(
        (found for found in candidates if _legs_agree(fingerprint[3], _fingerprint(found, account)[3])),
        None,
    )


def _source_amounts(entry: Any, account: str) -> str:
    # `:f` keeps the digits as written and out of scientific notation, which
    # `str()` chooses below one millionth (`-5.0E-7`) — a spelling input refuses.
    return ", ".join(f"{p.units.number:f} {p.units.currency}{_lot_text(p)}" for p in _source_postings(entry, account))


def _traceback(exc: BaseException) -> str:
    import traceback

    return "".join(traceback.format_exception(exc))
