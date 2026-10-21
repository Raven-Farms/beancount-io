import { FeedSource } from "../../../generated-graphql/types";

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
