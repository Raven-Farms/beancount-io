import { createFileRoute } from "@tanstack/react-router";
import LoginPage from "@/features/auth/pages/login-page";
import { z } from "zod";
import { searchEnum, searchString } from "@/common/lib/search-params/tolerant";
import { getSEOMetadata, createHeadMeta } from "@/common/lib/seo/seo-helpers";
import { loginBeforeLoad } from "@/features/auth/pages/login-page/loader";

const loginSearchSchema = z.object({
  next: searchString(),
  reason: searchEnum([
    "expired",
    "google_unavailable",
    "google_cancelled",
    "google_state",
    "google_failed",
    "google_unverified",
    "google_domain",
    "google_not_allowed",
    "google_blocked",
  ]),
});

export const Route = createFileRoute("/auth/login/")({
  component: LoginPage,
  beforeLoad: loginBeforeLoad,
  validateSearch: (search) => loginSearchSchema.parse(search),
  head: ({ match }) =>
    createHeadMeta(
      match.context.localization.i18n,
      getSEOMetadata(
        match.context.localization.i18n,
        "seo.login.title",
        "seo.login.description",
      ),
    ),
  // ssr: false,
});
