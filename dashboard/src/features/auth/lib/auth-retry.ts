import { CombinedGraphQLErrors } from "@apollo/client/errors";

/** Read only the bounded public retry metadata, never server error prose. */
export function readAuthRetry(error: unknown): {
  isRateLimited: boolean;
  retryAfter?: number;
} {
  if (!CombinedGraphQLErrors.is(error)) return { isRateLimited: false };
  const refusals = error.errors.filter(
    ({ extensions }) =>
      extensions?.code === "RATE_LIMITED" ||
      extensions?.code === "SERVICE_UNAVAILABLE",
  );
  const retries = refusals
    .map(({ extensions }) => extensions?.retryAfter)
    .filter(
      (value): value is number =>
        typeof value === "number" && Number.isFinite(value) && value > 0,
    );
  return {
    isRateLimited: refusals.some(
      ({ extensions }) => extensions?.code === "RATE_LIMITED",
    ),
    retryAfter: retries.length
      ? Math.min(86_400, Math.ceil(Math.max(...retries)))
      : undefined,
  };
}
