import { createFileRoute } from "@tanstack/react-router";
import LoginPage from "@/features/auth/pages/login-page";
import { z } from "zod";
import { searchEnum, searchString } from "@/common/lib/search-params/tolerant";
import { getSEOMetadata, createHeadMeta } from "@/common/lib/seo/seo-helpers";
import { loginBeforeLoad } from "@/features/auth/pages/login-page/loader";

const loginSearchSchema = z.object({
  next: searchString(),
  reason: searchEnum(["expired"]),
  recovery: z
    .unknown()
    .transform((value) =>
      typeof value === "string" && /^rcv_[a-f0-9]{64}$/.test(value)
        ? value
        : undefined,
    )
    .optional(),
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
