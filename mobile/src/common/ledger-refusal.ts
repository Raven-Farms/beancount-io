/**
 * What a refused structured write says it would break, or null when the error
 * is anything else. The server refuses entries that would add bean-check
 * errors — a second `open` for an account already open — as
 * `VALIDATION_FAILED` on the `entries` field, its reason ending in the errors
 * it names (w0/m2). The detail is the engine's own diagnosis, the same text the
 * ledger's error list shows. Free of `@/` imports so jest-lite can require it.
 */
export function newLedgerErrorDetail(error: unknown): string | null {
  if (typeof error !== "object" || error === null) return null;
  const gqlErrors = (error as { graphQLErrors?: unknown }).graphQLErrors;
  if (!Array.isArray(gqlErrors)) return null;
  for (const gqlError of gqlErrors) {
    const extensions = (
      gqlError as {
        extensions?: { code?: unknown; field?: unknown; reason?: unknown };
      }
    )?.extensions;
    if (
      extensions?.code !== "VALIDATION_FAILED" ||
      extensions.field !== "entries" ||
      typeof extensions.reason !== "string"
    ) {
      continue;
    }
    const detail = /new bean-check errors?: ([\s\S]+)$/.exec(
      extensions.reason,
    )?.[1];
    if (detail?.trim()) return detail.trim();
  }
  return null;
}
