import { CombinedGraphQLErrors } from "@apollo/client/errors";

export function isPlaidAccessError(error: Error) {
  return (
    CombinedGraphQLErrors.is(error) &&
    error.errors.some(
      ({ extensions }) =>
        extensions?.code === "FORBIDDEN" ||
        extensions?.code === "UNAUTHENTICATED",
    )
  );
}
