import { notFound } from "@tanstack/react-router";
import { rethrowEntityRouteError } from "@/common/lib/errors/entity-route-error";
import type { RouteLoader } from "@/common/types/route-loader";
import { GetUserProfileDocument } from "@/graphql/definitions";

export const userProfileLoader: RouteLoader<
  "/ledger/$username",
  { profileExists: true }
> = async ({ params, context, location }) => {
  let data;
  try {
    const result = await context.client.query({
      query: GetUserProfileDocument,
      variables: { username: params.username },
      fetchPolicy: "cache-first",
    });
    data = result.data;
  } catch (error) {
    rethrowEntityRouteError(error, location);
  }

  if (!data?.getUserProfile?.profile) throw notFound();
  return { profileExists: true };
};
