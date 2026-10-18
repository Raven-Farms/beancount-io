/**
 * The ledger (repository) name a typed name becomes, exactly as the ledger
 * service slugifies it (`backend-cluster/ledger/src/shared/ledger-name.ts`):
 * lowercase, spaces to hyphens, only `[a-z0-9_-]`, hyphens collapsed and
 * trimmed. The server stays the authority; this is for feedback.
 */
export function slugifyLedgerName(text: string): string {
  return text
    .toLowerCase()
    .replace(/ /g, "-")
    .replace(/[^a-z0-9_-]/g, "")
    .replace(/-+/g, "-")
    .replace(/^-+|-+$/g, "");
}

/** The longest name the ledger service accepts after slugifying. */
export const MAX_LEDGER_NAME_LENGTH = 100;
