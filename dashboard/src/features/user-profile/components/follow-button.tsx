import { Button } from "@/common/components/ui/button";
import { UserPlus, UserCheck } from "lucide-react";
import { useFollowUser } from "../hooks/use-follow-user";
import { useUnfollowUser } from "../hooks/use-unfollow-user";
import { useNavigate } from "@tanstack/react-router";
import { useTranslations } from "@/common/hooks/use-translations";
import { useIsAuthenticated } from "@/common/hooks/use-is-authenticated";
import { useLoginNextPath } from "@/common/hooks/use-login-next-path";

interface FollowButtonProps {
  username: string;
  isFollowing?: boolean;
  descriptionId?: string;
  className?: string;
}

export function FollowButton({
  username,
  isFollowing,
  descriptionId,
  className,
}: FollowButtonProps) {
  const navigate = useNavigate();
  const { t } = useTranslations();
  const { followUser, loading: followLoading } = useFollowUser();
  const { unfollowUser, loading: unfollowLoading } = useUnfollowUser();
  const isUserAuthenticated = useIsAuthenticated();
  const next = useLoginNextPath();

  const loading = followLoading || unfollowLoading;

  const handleClick = async () => {
    // If not logged in, redirect to login and come back to this profile after.
    if (!isUserAuthenticated) {
      void navigate({ to: "/auth/login", search: { next } });
      return;
    }

    // Toggle follow/unfollow
    try {
      if (isFollowing) {
        await unfollowUser({ variables: { username } });
      } else {
        await followUser({ variables: { username } });
      }
    } catch {
      // Mutation errors are handled by Apollo; prevent unhandled rejection
    }
  };

  return (
    <Button
      variant={isFollowing ? "outline" : "default"}
      size="default"
      onClick={handleClick}
      loading={loading}
      className={className}
      aria-describedby={descriptionId}
    >
      {isFollowing ? (
        <UserCheck className="size-4 mr-2" />
      ) : (
        <UserPlus className="size-4 mr-2" />
      )}
      {isFollowing ? t("userProfile.unfollow") : t("userProfile.follow")}
    </Button>
  );
}
