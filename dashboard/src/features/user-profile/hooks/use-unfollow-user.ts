import { useMutation } from "@apollo/client/react";
import {
  UnfollowUserDocument,
  GetUserProfileDocument,
  GetUserFollowersDocument,
  GetUserFollowingDocument,
} from "@/graphql/definitions";
import { toast } from "sonner";
import { useTranslations } from "@/common/hooks/use-translations";
import { updateFollowingCache } from "./update-following-cache";

export function useUnfollowUser() {
  const { t } = useTranslations();

  const [unfollowUser, { loading }] = useMutation(UnfollowUserDocument, {
    update: (cache, { data }, { variables }) => {
      if (data?.unfollowUser.success && variables?.username) {
        updateFollowingCache(cache, variables.username, false);
      }
    },
    onCompleted: (data, options) => {
      if (data.unfollowUser.success) {
        const username = options?.variables?.username || "";
        toast.success(
          data.unfollowUser.message ||
            t("userProfile.unfollowSuccess", { username }),
        );
      } else {
        toast.error(
          data.unfollowUser.message || t("userProfile.unfollowError"),
        );
      }
    },
    onError: (error) => {
      toast.error(t("userProfile.unfollowError"));
      console.error("Unfollow error:", error);
    },
    // Refetch user profile, followers, and following lists
    refetchQueries: [
      GetUserProfileDocument,
      GetUserFollowersDocument,
      GetUserFollowingDocument,
    ],
  });

  return { unfollowUser, loading };
}
