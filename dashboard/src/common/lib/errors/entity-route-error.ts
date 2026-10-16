import { CombinedGraphQLErrors } from "@apollo/client/errors";
import { notFound, redirect } from "@tanstack/react-router";
import { getSafeReturnPath } from "@/common/lib/auth/auth";

/** Classify entity lookup failures before SSR can serialize away error codes. */
export function rethrowEntityRouteError(
  error: unknown,
  location: { href: string },
): never {
  if (CombinedGraphQLErrors.is(error)) {
    const codes = error.errors.map((item) => item.extensions?.code);
    if (codes.includes("UNAUTHENTICATED")) {
      throw redirect({
        to: "/auth/login",
        search: { next: getSafeReturnPath(location) },
      });
    }
    if (
      codes.includes("FORBIDDEN") ||
      codes.includes("NOT_FOUND") ||
      codes.includes("BAD_USER_INPUT")
    ) {
      throw notFound();
    }
  }
  throw error;
}
