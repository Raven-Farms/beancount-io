/**
 * Helpers for `GET /ledgers/search`. Gitea's repo search matches the typed text
 * as ONE substring of the repository name (or description), so "crypto example"
 * never matched `crypto-example`, and an owner matched only through a
 * description (w21/245). The ledger service reads a query as words instead.
 */

/** The words of a query: split on whitespace, empty parts dropped. */
export function searchTerms(q: string | undefined): string[] {
  return (q ?? "").split(/\s+/).filter(Boolean);
}

/** Lower-cased, with the characters a ledger name is hyphenated with as spaces. */
export function normalizeSearchText(text: string): string {
  return text
    .toLowerCase()
    .split(/[\s\-_/.]+/)
    .filter(Boolean)
    .join(" ");
}

/**
 * Whether a repository's `owner/name` or description contains `term`, the way
 * a person reads it: "example" is in `open_ledger/crypto-example`, and so is
 * "ledger crypto".
 */
export function repoMatchesTerm(
  repo: { full_name?: string; description?: string | null },
  term: string,
): boolean {
  const wanted = normalizeSearchText(term);
  if (!wanted) return true;
  return normalizeSearchText(
    `${repo.full_name ?? ""} ${repo.description ?? ""}`,
  ).includes(wanted);
}

/**
 * Whether `term` can be a Gitea user or organization name. Only these are
 * looked up as an owner, so a word like "my book" or a path never costs a
 * request.
 */
export function mightBeOwnerName(term: string): boolean {
  return /^[A-Za-z0-9][A-Za-z0-9._-]{0,38}$/.test(term);
}

/** Keeps the first of repeated ids, in order. */
export function dedupeById<T extends { id?: number }>(repos: T[]): T[] {
  const seen = new Set<number | undefined>();
  const out: T[] = [];
  for (const repo of repos) {
    if (repo.id !== undefined && seen.has(repo.id)) continue;
    seen.add(repo.id);
    out.push(repo);
  }
  return out;
}
