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

/** The URL path segments backend-v2 accepts (`shared/ledger-slug.ts`). */
export const LEDGER_OWNER_PATTERN = /^(?!\.{1,2}$)[A-Za-z0-9_.-]+$/;
export const LEDGER_NAME_PATTERN = /^[a-z0-9_-]{1,100}$/;

/**
 * The ledger name a typed or pasted URL segment means: lowercased, without a
 * git remote's `.git`. `null` when no ledger could have that name.
 */
export function canonicalLedgerSlug(segment: string): string | null {
  const slug = segment.toLowerCase().replace(/\.git$/, "");
  return LEDGER_NAME_PATTERN.test(slug) ? slug : null;
}
