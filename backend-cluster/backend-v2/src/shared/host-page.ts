import { BadUserInputError } from "@/shared/errors";

/**
 * The most items the repository host returns in one page (Gitea's
 * `MAX_RESPONSE_ITEMS`). It answers a larger `limit` with this many, which a
 * caller reads as the last page, and an out-of-range page or limit with its
 * own defaults (w21/314, w23/038).
 */
export const HOST_PAGE_MAX = 50;

/** Refuse a page or limit the host would silently replace. */
export function assertHostPage(
  page: number | undefined,
  limit: number | undefined,
): void {
  for (const [name, value] of [
    ["page", page],
    ["limit", limit],
  ] as const) {
    if (value !== undefined && (!Number.isInteger(value) || value < 1)) {
      throw new BadUserInputError(`${name} must be a positive integer`, name);
    }
  }
  if (limit !== undefined && limit > HOST_PAGE_MAX) {
    throw new BadUserInputError(
      `limit must be at most ${HOST_PAGE_MAX}`,
      "limit",
    );
  }
}
