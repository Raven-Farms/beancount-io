import { createFileRoute } from "@tanstack/react-router";
import GalleryPage from "@/features/ledger-list/pages/gallery-page";
import { validateGallerySearch } from "@/features/ledger-list/pages/gallery-page/search";
import { requireAuth } from "@/common/lib/auth/auth";
import { getSEOMetadata, createHeadMeta } from "@/common/lib/seo/seo-helpers";

export const Route = createFileRoute("/ledger-gallery")({
  validateSearch: validateGallerySearch,
  component: GalleryPage,
  beforeLoad: requireAuth("/ledger-gallery"),
  head: ({ match }) =>
    createHeadMeta(
      match.context.localization.i18n,
      getSEOMetadata(
        match.context.localization.i18n,
        "seo.ledgerGallery.title",
        "seo.ledgerGallery.description",
      ),
      { noIndex: true },
    ),
});
