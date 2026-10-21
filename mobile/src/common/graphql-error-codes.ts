/** The `extensions` of every GraphQL error an Apollo error carries. */
export function graphQLErrorExtensions(
  err: unknown,
): Record<string, unknown>[] {
  if (typeof err !== "object" || err === null) return [];
  const gqlErrors = (err as { graphQLErrors?: unknown }).graphQLErrors;
  if (!Array.isArray(gqlErrors)) return [];
  return gqlErrors.flatMap((e) => {
    const extensions = (e as { extensions?: unknown } | null)?.extensions;
    return typeof extensions === "object" && extensions !== null
      ? [extensions as Record<string, unknown>]
      : [];
  });
}

/** The `extensions.code` of every GraphQL error an Apollo error carries. */
export function graphQLErrorCodes(err: unknown): string[] {
  return graphQLErrorExtensions(err).flatMap(({ code }) =>
    typeof code === "string" ? [code] : [],
  );
}

/**
 * Whether a read of the selected ledger answered that it no longer exists —
 * deleted, renamed, or access withdrawn on the web. Every Home card used to
 * show its own "Failed to load · Try again", which could never succeed
 * (w21/054). A network failure is not "gone".
 */
export function isLedgerGone(err: unknown): boolean {
  return graphQLErrorCodes(err).includes("NOT_FOUND");
}
