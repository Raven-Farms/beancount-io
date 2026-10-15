import { CombinedGraphQLErrors } from "@apollo/client/errors";

/**
 * The server's answer for a code no terminal issued, or one that expired:
 * `CLI auth session not found or expired` (BAD_USER_INPUT). It deserves its
 * own message — the generic "information provided is invalid" never said the
 * code was the problem or where a new one comes from (w0/019).
 */
export function isUnknownCliCodeError(error: unknown): boolean {
  return (
    CombinedGraphQLErrors.is(error) &&
    error.errors.some(
      (gqlError) =>
        ["BAD_USER_INPUT", "NOT_FOUND"].includes(
          String(gqlError.extensions?.code),
        ) && /not found or expired/i.test(gqlError.message),
    )
  );
}
