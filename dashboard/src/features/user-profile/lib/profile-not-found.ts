import { CombinedGraphQLErrors } from "@apollo/client/errors";

export function isProfileNotFound(error: unknown): boolean {
  if (!CombinedGraphQLErrors.is(error)) return false;
  const codes = error.errors.map((item) => item.extensions?.code);
  return (
    !codes.includes("UNAUTHENTICATED") &&
    codes.some((code) =>
      ["NOT_FOUND", "BAD_USER_INPUT", "FORBIDDEN"].includes(String(code)),
    )
  );
}
