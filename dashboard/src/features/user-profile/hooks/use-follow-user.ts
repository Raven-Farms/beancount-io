import { useMutation } from "@apollo/client/react";
import {
  FollowUserDocument,
  GetUserProfileDocument,
  GetUserFollowersDocument,
  GetUserFollowingDocument,
} from "@/graphql/definitions";
import { toast } from "sonner";
import { useTranslations } from "@/common/hooks/use-translations";
import { updateFollowingCache } from "./update-following-cache";

export function useFollowUser() {
  const { t } = useTranslations();

  const [followUser, { loading }] = useMutation(FollowUserDocument, {
    update: (cache, { data }, { variables }) => {
      if (data?.followUser.success && variables?.username) {
        updateFollowingCache(cache, variables.username, true);
      }
    },
    onCompleted: (data, options) => {
      if (data.followUser.success) {
        const username = options?.variables?.username || "";
        toast.success(
          data.followUser.message ||
            t("userProfile.followSuccess", { username }),
        );
      } else {
        toast.error(data.followUser.message || t("userProfile.followError"));
      }
    },
    onError: (error) => {
      toast.error(t("userProfile.followError"));
      console.error("Follow error:", error);
    },
    // Refetch user profile, followers, and following lists
    refetchQueries: [
      GetUserProfileDocument,
      GetUserFollowersDocument,
      GetUserFollowingDocument,
    ],
  });

  return { followUser, loading };
}
