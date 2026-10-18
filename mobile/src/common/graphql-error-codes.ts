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
