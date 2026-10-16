import type { ApolloCache } from "@apollo/client";
import { GetUserProfileDocument } from "@/graphql/definitions";

/** Publish a confirmed mutation before the profile's background refetch starts. */
export function updateFollowingCache(
  cache: ApolloCache,
  username: string,
  following: boolean,
) {
  cache.updateQuery(
    { query: GetUserProfileDocument, variables: { username } },
    (cached) =>
      cached?.getUserProfile
        ? {
            ...cached,
            getUserProfile: {
              ...cached.getUserProfile,
              isFollowing: following,
            },
          }
        : cached,
  );
}
