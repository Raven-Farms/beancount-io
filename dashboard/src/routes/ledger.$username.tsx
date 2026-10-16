import { createFileRoute } from "@tanstack/react-router";
import UserProfilePage from "@/features/user-profile/pages/user-profile-page";
import { getSEOMetadata, createHeadMeta } from "@/common/lib/seo/seo-helpers";
import { userProfileSearchSchema } from "@/features/user-profile/lib/search";
import { userProfileLoader } from "@/features/user-profile/loader";
import { UserProfileNotFoundPage } from "@/features/user-profile/pages/user-profile-not-found-page";

export const Route = createFileRoute("/ledger/$username")({
  component: UserProfilePage,
  loader: userProfileLoader,
  notFoundComponent: UserProfileNotFoundPage,
  validateSearch: (search) => userProfileSearchSchema.parse(search),
  head: ({ params, match, loaderData }) =>
    !loaderData?.profileExists ||
    match.status === "error" ||
    match.status === "notFound"
      ? { meta: [], links: [] }
      : createHeadMeta(
          match.context.localization.i18n,
          getSEOMetadata(
            match.context.localization.i18n,
            "seo.userProfile.title",
            "seo.userProfile.description",
            {
              username: params.username,
            },
          ),
        ),
});
