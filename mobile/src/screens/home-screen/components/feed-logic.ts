import { FeedSource } from "../../../generated-graphql/types";
import {
  normalizeOrigin,
  resolveAppLink,
  type AppLinkTarget,
} from "../../../common/app-links/resolve-app-link";

export type FeedSourceLabelKey =
  "feedSourceLedger" | "feedSourceBlog" | "feedSourceRelease";

/**
 * Translation key for the source label of a feed row. Product releases arrive
 * from the changelog feed and used to be labelled "Blog" alongside marketing
 * posts, which is the one thing they are not.
 */
export function feedSourceLabelKey(source: FeedSource): FeedSourceLabelKey {
  switch (source) {
    case FeedSource.LedgerRss:
      return "feedSourceLedger";
    case FeedSource.Changelog:
      return "feedSourceRelease";
    default:
      return "feedSourceBlog";
  }
}

/**
 * The feed's query variables. The feed is asked for in the app's language:
 * pinned to "en", a German app listed English titles that opened `/blog/…`
 * instead of `/de/blog/…` (w21/136). Being a variable, a language change
 * refetches.
 */
export function feedQueryVariables(limit: number, locale: string) {
  return { offset: 0, limit, locale };
}

export type FeedRowAction =
  | { kind: "external"; url: string }
  | { kind: "ledger"; target: AppLinkTarget; sourceUrl: string };

/**
 * What tapping a feed row does. Blog and release rows link out; ledger
 * activity carries a relative `/ledger/<owner>/<name>[/commit/<sha>]` path,
 * which the row ignored, so "Committed to …" rows looked tappable and did
 * nothing (w21/137). Those open in the app as the same URL would. A row
 * whose link resolves to nothing is not a button.
 */
export function feedRowAction(
  link: string,
  serverUrl: string,
): FeedRowAction | null {
  if (/^https?:\/\//.test(link)) return { kind: "external", url: link };
  if (!link.startsWith("/ledger/")) return null;
  const sourceUrl = `${normalizeOrigin(serverUrl)}${link}`;
  const target = resolveAppLink(sourceUrl, { serverUrl });
  return target ? { kind: "ledger", target, sourceUrl } : null;
}

/**
 * Whether a row's date is a calendar day rather than an instant. Blog and
 * release posts are date-only and arrive as midnight UTC; ledger activity
 * is a real commit time, read in the device's zone (w21/147).
 */
export function feedDateIsCalendarDay(source: FeedSource): boolean {
  return source !== FeedSource.LedgerRss;
}
