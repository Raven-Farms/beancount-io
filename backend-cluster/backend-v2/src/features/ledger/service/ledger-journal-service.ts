import { parseLedgerId } from "@/shared/str";
import {
  unwrapFavaResponse,
  type DirectiveType,
  type TransactionSubtype,
  type DocumentSubtype,
  type CustomSubtype,
} from "@/foundation/fava";
import type { Identity } from "@/server/api/identity";
import {
  authorizeLedger,
  AuthorizedLedgerService,
} from "@/features/ledger/utils/authorize-ledger";
import {
  AUTHORIZATION_ACTIONS,
  type AuthorizationAction,
} from "@/server/api/authorization/authorization-contract";
import { BadUserInputError } from "@/shared/errors";

/**
 * The page a journal read asks for: limit 1–1000 (default 20), offset 0 or
 * more (default 0), both safe integers.
 *
 * Checked here because GraphQL's `Number` arguments arrive unchecked, and the
 * ledger pages with `items.slice(offset, offset + limit)`: a negative limit
 * silently dropped the last entries, a fraction truncated, and zero answered
 * an empty page beside a nonzero total (w6/007). REST and MCP refuse the same
 * values in their schemas; this holds GraphQL to that contract before any
 * authorization or ledger work, as the commits service does for its pages.
 */
function journalPage(query?: { limit?: number; offset?: number }): {
  limit: number;
  offset: number;
} {
  const limit = query?.limit ?? 20;
  const offset = query?.offset ?? 0;
  if (!Number.isSafeInteger(limit) || limit < 1 || limit > 1000) {
    throw new BadUserInputError(
      "limit must be an integer from 1 to 1000",
      "limit",
    );
  }
  if (!Number.isSafeInteger(offset) || offset < 0) {
    throw new BadUserInputError(
      "offset must be a non-negative integer",
      "offset",
    );
  }
  return { limit, offset };
}

export type JournalResult = {
  total: number;
  data: Record<string, unknown>[];
  is_empty: boolean;
};

export type EntryContextResult = {
  entry: Record<string, unknown>;
  balances_before?: Record<string, string[]> | null;
  balances_after?: Record<string, string[]> | null;
  sha256sum: string;
  slice: string;
  /**
   * The feed URL when the entry comes from a managed price include (ADR 015),
   * else null: the entry is read-only, with no source file to open.
   */
  managed_source: string | null;
};

export type PlaintextJournalResult = { content: string };

export type AccountJournalResult = {
  items: {
    entry: Record<string, unknown>;
    change: Record<string, string>;
    balance: Record<string, string>;
  }[];
  total: number;
  account: string;
  with_children: boolean;
};

export type DeleteSliceResult = { message: string; entryHash: string };

export type DeleteMultiSlicesResult = {
  message: string;
  /** How many entries were deleted — hashes are stale the moment they are. */
  deletedCount: number;
};

export type UpdateSliceResult = {
  message: string;
  entryHash: string;
  newSha256sum: string;
  /** The entry's public ID after the commit, re-read post-commit (w2/m26). */
  newEntryHash: string;
};

export type JournalQueryParams = {
  account?: string;
  filter?: string;
  time?: string;
  directiveTypes?: DirectiveType[];
  transactionSubtypes?: TransactionSubtype[];
  documentSubtypes?: DocumentSubtype[];
  customSubtypes?: CustomSubtype[];
  limit?: number;
  offset?: number;
};

export type AccountJournalQueryParams = {
  account: string;
  /** Shared report-stream AccountFilter; maps to ledger `filter_account`. */
  filterAccount?: string;
  filter?: string;
  time?: string;
  directiveTypes?: DirectiveType[];
  transactionSubtypes?: TransactionSubtype[];
  documentSubtypes?: DocumentSubtype[];
  customSubtypes?: CustomSubtype[];
  limit?: number;
  offset?: number;
  with_children?: boolean;
  conversion?: string;
};

export interface ILedgerJournalService {
  getJournal(params: {
    ledgerId: string;
    identity: Identity | undefined;
    query?: JournalQueryParams;
  }): Promise<JournalResult>;

  getContext(params: {
    ledgerId: string;
    identity: Identity | undefined;
    entryHash: string;
  }): Promise<EntryContextResult>;

  plaintextJournal(params: {
    ledgerId: string;
    identity: Identity | undefined;
    query?: { account?: string; filter?: string; time?: string };
  }): Promise<PlaintextJournalResult>;

  getAccountJournal(params: {
    ledgerId: string;
    identity: Identity | undefined;
    query: AccountJournalQueryParams;
  }): Promise<AccountJournalResult>;

  deleteSourceSlice(params: {
    ledgerId: string;
    identity: Identity;
    entryHash: string;
    sha256sum: string;
  }): Promise<DeleteSliceResult>;

  deleteMultiSourceSlices(params: {
    ledgerId: string;
    identity: Identity;
    entries: { entryHash: string; sha256sum: string }[];
  }): Promise<DeleteMultiSlicesResult>;

  updateSourceSlice(params: {
    ledgerId: string;
    identity: Identity;
    entryHash: string;
    sha256sum: string;
    newContent: string;
  }): Promise<UpdateSliceResult>;
}

export class LedgerJournalService
  extends AuthorizedLedgerService
  implements ILedgerJournalService
{
  /** Shared by all seven verbs: authorize, then hand back a ready Fava client. */
  private async getClient(
    ledgerId: string,
    identity: Identity | undefined,
    action: AuthorizationAction,
  ) {
    await authorizeLedger(identity, ledgerId, action, this.authDeps);
    const { ledgerOwner, ledgerName } = parseLedgerId(ledgerId);
    const favaApiClient = await this.favaClientFactory.getPublicApiClient(
      ledgerId,
      identity?.userId,
    );
    return { favaApiClient, ledgerOwner, ledgerName };
  }

  async getJournal(params: {
    ledgerId: string;
    identity: Identity | undefined;
    query?: JournalQueryParams;
  }): Promise<JournalResult> {
    const { ledgerId, identity, query } = params;
    const page = journalPage(query);
    const { favaApiClient, ledgerOwner, ledgerName } = await this.getClient(
      ledgerId,
      identity,
      AUTHORIZATION_ACTIONS.LEDGER_JOURNAL_READ,
    );

    const data = await unwrapFavaResponse(
      favaApiClient.journal.getJournal(ledgerOwner, ledgerName, {
        account: query?.account || undefined,
        filter: query?.filter || undefined,
        time: query?.time || undefined,
        directive_types: query?.directiveTypes || undefined,
        ...page,
        transaction_subtypes: query?.transactionSubtypes || undefined,
        document_subtypes: query?.documentSubtypes || undefined,
        custom_subtypes: query?.customSubtypes || undefined,
      }),
      "get ledger journal entries",
    );
    return {
      total: data.total,
      data: data.items as unknown as Record<string, unknown>[],
      is_empty: data.is_empty,
    };
  }

  async getContext(params: {
    ledgerId: string;
    identity: Identity | undefined;
    entryHash: string;
  }): Promise<EntryContextResult> {
    const { ledgerId, identity, entryHash } = params;
    const { favaApiClient, ledgerOwner, ledgerName } = await this.getClient(
      ledgerId,
      identity,
      AUTHORIZATION_ACTIONS.LEDGER_JOURNAL_READ,
    );

    // Entry hashes are content-derived, so a stale hash is a NORMAL outcome
    // after an edit: the ledger service answers 404/409, which unwrapFavaResponse
    // maps to NotFound/Conflict instead of an opaque 500.
    const ctx = await unwrapFavaResponse(
      favaApiClient.journal.getContext(ledgerOwner, ledgerName, entryHash),
      "get entry context",
    );
    return {
      entry: ctx.entry as unknown as Record<string, unknown>,
      balances_before: ctx.balances_before,
      balances_after: ctx.balances_after,
      sha256sum: ctx.sha256sum,
      slice: ctx.slice,
      managed_source: ctx.managed_source ?? null,
    };
  }

  async plaintextJournal(params: {
    ledgerId: string;
    identity: Identity | undefined;
    query?: { account?: string; filter?: string; time?: string };
  }): Promise<PlaintextJournalResult> {
    const { ledgerId, identity, query } = params;
    const { favaApiClient, ledgerOwner, ledgerName } = await this.getClient(
      ledgerId,
      identity,
      AUTHORIZATION_ACTIONS.LEDGER_JOURNAL_READ,
    );

    const data = await unwrapFavaResponse(
      favaApiClient.journal.plaintextJournal(ledgerOwner, ledgerName, {
        account: query?.account || undefined,
        filter: query?.filter || undefined,
        time: query?.time || undefined,
      }),
      "get plaintext journal",
    );
    return { content: data.content };
  }

  async getAccountJournal(params: {
    ledgerId: string;
    identity: Identity | undefined;
    query: AccountJournalQueryParams;
  }): Promise<AccountJournalResult> {
    const { ledgerId, identity, query } = params;
    const page = journalPage(query);
    const { favaApiClient, ledgerOwner, ledgerName } = await this.getClient(
      ledgerId,
      identity,
      AUTHORIZATION_ACTIONS.LEDGER_JOURNAL_READ,
    );

    const data = await unwrapFavaResponse(
      favaApiClient.journal.getAccountJournal(ledgerOwner, ledgerName, {
        account: query.account,
        filter_account: query.filterAccount || undefined,
        filter: query.filter || undefined,
        time: query.time || undefined,
        ...page,
        with_children:
          query.with_children !== undefined ? query.with_children : true,
        conversion: query.conversion || "at_cost",
        directive_types: query.directiveTypes || undefined,
        transaction_subtypes: query.transactionSubtypes || undefined,
        document_subtypes: query.documentSubtypes || undefined,
        custom_subtypes: query.customSubtypes || undefined,
      }),
      "get account journal entries",
    );
    return {
      items: data.items.map((item) => ({
        entry: item.entry as unknown as Record<string, unknown>,
        change: item.change,
        balance: item.balance,
      })),
      total: data.total,
      account: data.account,
      with_children: data.with_children,
    };
  }

  async deleteSourceSlice(params: {
    ledgerId: string;
    identity: Identity;
    entryHash: string;
    sha256sum: string;
  }): Promise<DeleteSliceResult> {
    const { ledgerId, identity, entryHash, sha256sum } = params;
    const { favaApiClient, ledgerOwner, ledgerName } = await this.getClient(
      ledgerId,
      identity,
      AUTHORIZATION_ACTIONS.LEDGER_ENTRIES_WRITE,
    );

    const data = await unwrapFavaResponse(
      favaApiClient.journal.deleteSourceSlice(ledgerOwner, ledgerName, {
        entry_hash: entryHash,
        sha256sum,
      }),
      "delete source slice",
    );
    return { message: data.message, entryHash: data.entry_hash };
  }

  async deleteMultiSourceSlices(params: {
    ledgerId: string;
    identity: Identity;
    entries: { entryHash: string; sha256sum: string }[];
  }): Promise<DeleteMultiSlicesResult> {
    const { ledgerId, identity, entries } = params;
    const { favaApiClient, ledgerOwner, ledgerName } = await this.getClient(
      ledgerId,
      identity,
      AUTHORIZATION_ACTIONS.LEDGER_ENTRIES_WRITE,
    );

    const data = await unwrapFavaResponse(
      favaApiClient.journal.deleteMultiSourceSlices(ledgerOwner, ledgerName, {
        entries: entries.map((e) => ({
          entry_hash: e.entryHash,
          sha256sum: e.sha256sum,
        })),
      }),
      "delete source slices",
    );
    return { message: data.message, deletedCount: data.deleted_hashes.length };
  }

  async updateSourceSlice(params: {
    ledgerId: string;
    identity: Identity;
    entryHash: string;
    sha256sum: string;
    newContent: string;
  }): Promise<UpdateSliceResult> {
    const { ledgerId, identity, entryHash, sha256sum, newContent } = params;
    const { favaApiClient, ledgerOwner, ledgerName } = await this.getClient(
      ledgerId,
      identity,
      AUTHORIZATION_ACTIONS.LEDGER_ENTRIES_WRITE,
    );

    const data = await unwrapFavaResponse(
      favaApiClient.journal.updateSourceSlice(ledgerOwner, ledgerName, {
        entry_hash: entryHash,
        sha256sum,
        new_content: newContent,
      }),
      "update source slice",
    );
    return {
      message: data.message,
      // The entry's NEW content-derived hash (the ledger service resolves it
      // from the committed content), not an echo of the request.
      entryHash: data.entry_hash,
      newSha256sum: data.new_sha256sum,
      newEntryHash: data.new_entry_hash,
    };
  }
}
