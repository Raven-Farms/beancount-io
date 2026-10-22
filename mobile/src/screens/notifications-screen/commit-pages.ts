/** Commits per page the Recent changes list asks the server for. */
export const COMMITS_PAGE_SIZE = 30;

/**
 * The older page appended to the commits already shown. Commits are keyed by
 * sha, so one that reappears across pages (a commit landing between the two
 * reads shifts the pages) is listed once, in its first position (w21/313).
 */
export function appendCommitPage<T extends { sha: string }>(
  shown: readonly T[],
  older: readonly T[],
): T[] {
  const seen = new Set(shown.map((commit) => commit.sha));
  return [...shown, ...older.filter((commit) => !seen.has(commit.sha))];
}

/** A page shorter than the page size is the last: there is nothing older. */
export function isLastCommitPage(page: readonly unknown[]): boolean {
  return page.length < COMMITS_PAGE_SIZE;
}

/**
 * How many pages the commits shown add up to. The list, not a counter kept
 * beside it, says where the next page starts: a write or a foreground refresh
 * refetches the first page and drops the rest, and a counter left at 2 then
 * skipped a page (w21/431). A commit listed once across a shifted page leaves
 * the count a few short of a whole number of pages, which still rounds up to
 * the page it came from.
 */
export function shownCommitPages(count: number): number {
  return Math.max(1, Math.ceil(count / COMMITS_PAGE_SIZE));
}
