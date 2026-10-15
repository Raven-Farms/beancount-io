import { createFileRoute, notFound, redirect } from "@tanstack/react-router";
import { CombinedGraphQLErrors } from "@apollo/client/errors";
import { GetLedgerAssetDownloadUrlDocument } from "@/graphql/definitions";
import { AttachmentUnavailablePage } from "@/common/root-route/not-found-page";

/**
 * Receipt links written into ledgers (`/ledger_assets/<repo>/static/<file>`)
 * outlive their assets and reach readers without access. A missing, foreign
 * or malformed target is a 404 "attachment unavailable", not a 500
 * "unexpected error" (w0/018); a signed-out reader still goes through the
 * root error page's login redirect.
 */
const UNAVAILABLE_CODES = new Set(["NOT_FOUND", "FORBIDDEN", "BAD_USER_INPUT"]);

export const Route = createFileRoute("/ledger_assets/$ledgerRepoId/static/$")({
  beforeLoad: async ({ context, params }) => {
    const ledgerRepoId = Number(params.ledgerRepoId);
    const filename = params._splat ?? "";
    if (!Number.isSafeInteger(ledgerRepoId) || ledgerRepoId <= 0 || !filename) {
      throw notFound();
    }

    let downloadUrl: string | undefined;
    try {
      const result = await context.client.query({
        query: GetLedgerAssetDownloadUrlDocument,
        variables: { ledgerRepoId, filename },
        fetchPolicy: "no-cache",
      });
      downloadUrl = result.data?.getLedgerAssetDownloadUrl.downloadUrl;
    } catch (error) {
      if (
        CombinedGraphQLErrors.is(error) &&
        error.errors.some((gqlError) =>
          UNAVAILABLE_CODES.has(String(gqlError.extensions?.code)),
        )
      ) {
        throw notFound();
      }
      throw error;
    }
    if (!downloadUrl) throw notFound();

    throw redirect({ href: downloadUrl });
  },
  component: () => null,
  notFoundComponent: AttachmentUnavailablePage,
});
