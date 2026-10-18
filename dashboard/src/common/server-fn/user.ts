import { CombinedGraphQLErrors } from "@apollo/client/errors";
import { getClient } from "@/common/apollo/client";
import { getErrorMessageKey } from "@/common/lib/errors/error-message";
import {
  GetCurrentUserDocument,
  type GetCurrentUserQuery,
} from "@/graphql/definitions";

export type UserProfile = NonNullable<GetCurrentUserQuery["userProfile"]>;

/**
 * The identity probe has three outcomes, not two. A transport or 5xx failure
 * says nothing about the session, so it must stay distinguishable from "no
 * session": treating an outage as signed-out sends a signed-in user to the
 * login form (w3/646).
 */
export type AuthStatus = "signed-in" | "signed-out" | "unavailable";

export type UserProfileResult =
  | { status: "signed-in"; profile: UserProfile }
  | { status: "signed-out" }
  | { status: "unavailable"; error: Error };

export async function fetchUserProfile(
  defaultClient?: ReturnType<typeof getClient>,
): Promise<UserProfileResult> {
  const client = defaultClient ?? getClient();
  try {
    const result = await client.query({
      query: GetCurrentUserDocument,
      fetchPolicy: "network-only",
    });
    const profile = result.data?.userProfile ?? null;
    // The resolver is anonymous-reachable and answers null with no session.
    return profile
      ? { status: "signed-in", profile }
      : { status: "signed-out" };
  } catch (error) {
    // Same classification as `isUnauthenticatedError`, inlined so this
    // module stays free of the auth link's import chain.
    const unauthenticated =
      CombinedGraphQLErrors.is(error) &&
      error.errors.some(
        (gqlError) => gqlError.extensions?.code === "UNAUTHENTICATED",
      );
    if (unauthenticated) return { status: "signed-out" };
    // Route context cannot carry `unknown`; every Apollo failure is already
    // an Error, so only exotic non-Error throws are wrapped.
    return {
      status: "unavailable",
      error:
        error instanceof Error
          ? error
          : new Error("Authentication unavailable", { cause: error }),
    };
  }
}

/**
 * The root route context a profile result contributes. Route context must
 * stay serializable, so an unavailable probe contributes the localized
 * message key for its failure instead of the live Error.
 */
export function toAuthContext(result: UserProfileResult): {
  userProfile: UserProfile | null;
  authStatus: AuthStatus;
  authErrorKey: string | undefined;
} {
  return {
    userProfile: result.status === "signed-in" ? result.profile : null,
    authStatus: result.status,
    authErrorKey:
      result.status === "unavailable"
        ? getErrorMessageKey(result.error)
        : undefined,
  };
}
