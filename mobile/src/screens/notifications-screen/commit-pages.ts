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

/**
 * Whether an older page repeats a commit already shown. Paging is by offset, so
 * commits landing while the screen is open shift every page: page 2 then starts
 * with rows already shown, and with 30 or more new commits it is exactly them,
 * so Show older asked for it again and again, and the newest rows it did reach
 * were appended below older ones. The list has moved; it is read again from its
 * first page, where the new commits now sit (w21/626).
 */
export function commitPageOverlaps(
  shown: readonly { sha: string }[],
  older: readonly { sha: string }[],
): boolean {
  const seen = new Set(shown.map((commit) => commit.sha));
  return older.some((commit) => seen.has(commit.sha));
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

/**
 * Whether the rows shown reach the end the last short page left. The end is a
 * row count, not a page number: with a whole number of pages (30, 60 commits)
 * the empty page after them adds no rows, so a page number never caught up
 * (w21/498). A refetch to the first page has fewer rows than the end, so the
 * button returns.
 */
export function historyEnded(
  shownRows: number,
  endRows: number | null,
): boolean {
  return endRows !== null && shownRows >= endRows;
}

/** Where the history was found to end: the rows then, and the newest commit. */
export interface HistoryEnd {
  rows: number;
  head: string | undefined;
}

/**
 * The end still standing for the list now. A new commit changes the newest sha
 * and moves every page by one, so an end found before it no longer holds: the
 * oldest commit sits one row past it (w21/512).
 */
export function endRowsFor(
  end: HistoryEnd | null,
  head: string | undefined,
): number | null {
  return end !== null && end.head === head ? end.rows : null;
}
