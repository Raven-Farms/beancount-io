import { notFound } from "@tanstack/react-router";
import { rethrowEntityRouteError } from "@/common/lib/errors/entity-route-error";
import type { RouteLoader } from "@/common/types/route-loader";
import { GetLedgerFileDocument } from "@/graphql/definitions";

/**
 * Confirm the file exists before SSR, so a stale link answers 404 with
 * noindex instead of an indexable page that later says "File not found". A
 * path the server refuses (`../secret`) is not found too, never a retryable
 * outage. Same variables as the file view, so its query reads this result.
 */
export const fileLoader: RouteLoader<
  "/ledger/$ledgerOwner/$ledgerName/files/blob/$branch/$"
> = async ({ params, context, location }) => {
  try {
    const { data } = await context.client.query({
      query: GetLedgerFileDocument,
      variables: {
        ledgerId: `${params.ledgerOwner}/${params.ledgerName}`,
        path: params._splat ?? "",
      },
      fetchPolicy: "cache-first",
    });
    if (!data?.getLedgerFile) throw notFound();
  } catch (error) {
    rethrowEntityRouteError(error, location);
  }
};
