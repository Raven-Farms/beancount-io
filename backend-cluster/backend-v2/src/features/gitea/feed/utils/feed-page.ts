import { BadUserInputError } from "@/shared/errors";

/** The most items one feed page may hold. */
export const FEED_PAGE_MAX = 100;

/**
 * A negative or fractional page leaked JavaScript's `slice` semantics:
 * `limit=-1` returned all but the last item, `offset=-3` the oldest two
 * (w23/045). Checked here because GraphQL's Float arguments arrive unchecked;
 * they stay Float because clients already send them as Float variables.
 */
export function assertFeedPage(
  offset: number | undefined,
  limit: number | undefined,
) {
  if (offset !== undefined && (!Number.isInteger(offset) || offset < 0)) {
    throw new BadUserInputError(
      "offset must be a non-negative integer",
      "offset",
    );
  }
  if (
    limit !== undefined &&
    (!Number.isInteger(limit) || limit < 1 || limit > FEED_PAGE_MAX)
  ) {
    throw new BadUserInputError(
      `limit must be an integer from 1 to ${FEED_PAGE_MAX}`,
      "limit",
    );
  }
}
