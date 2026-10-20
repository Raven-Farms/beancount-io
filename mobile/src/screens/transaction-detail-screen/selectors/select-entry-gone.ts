import { graphQLErrorCodes } from "../../../common/graphql-error-codes";

/**
 * Whether the entry context answered that this entry no longer exists — it
 * was changed (a new content hash) or removed by an agent, the CLI or the web
 * since the list was loaded. The screen then stops presenting the cached copy
 * as current and offers no link to it (w21/013). A network or server failure
 * is not "gone": it stays a retryable error.
 */
export function isEntryGone(contextError: unknown): boolean {
  return graphQLErrorCodes(contextError).includes("NOT_FOUND");
}
