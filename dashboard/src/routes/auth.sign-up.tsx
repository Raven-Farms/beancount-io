import { createFileRoute } from "@tanstack/react-router";
import RegisterFlow from "@/features/auth/pages/register";
import { z } from "zod";
import {
  searchBoolean,
  searchString,
} from "@/common/lib/search-params/tolerant";
import { getSEOMetadata, createHeadMeta } from "@/common/lib/seo/seo-helpers";
import { registerBeforeLoad } from "@/features/auth/pages/register/loader";

const signUpSearchSchema = z.object({
  withDefaultLedger: searchBoolean(),
  src: searchString(),
  by: searchString(),
  // Post-signup destination (e.g. the marketing /pricing page's paid-plan
  // CTAs pass ?next=%2Fpricing). Validated by getSafeRedirectPath before use.
  next: searchString(),
});

export const Route = createFileRoute("/auth/sign-up")({
  component: RegisterFlow,
  beforeLoad: registerBeforeLoad,
  validateSearch: (search) => signUpSearchSchema.parse(search),
  head: ({ match }) =>
    createHeadMeta(
      match.context.localization.i18n,
      getSEOMetadata(
        match.context.localization.i18n,
        "seo.signUp.title",
        "seo.signUp.description",
      ),
    ),
});
