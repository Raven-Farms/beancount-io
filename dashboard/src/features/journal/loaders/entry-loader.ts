import { notFound } from "@tanstack/react-router";
import type { RouterContext } from "@/common/types/router-context";
import { rethrowEntityRouteError } from "@/common/lib/errors/entity-route-error";
import { GetLedgerEntryContextDocument } from "@/graphql/definitions";

export async function loadEntryRoute({
  context,
  params,
  location,
}: {
  context: Pick<RouterContext, "client">;
  params: { ledgerOwner: string; ledgerName: string; entryHash: string };
  location: { href: string };
}) {
  try {
    const { data } = await context.client.query({
      query: GetLedgerEntryContextDocument,
      variables: {
        ledgerId: `${params.ledgerOwner}/${params.ledgerName}`,
        entryHash: params.entryHash,
      },
      fetchPolicy: "cache-first",
    });
    if (!data?.getLedgerEntryContext?.entry) throw notFound();
  } catch (error) {
    rethrowEntityRouteError(error, location);
  }
}
