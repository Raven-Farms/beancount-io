import { notFound } from "@tanstack/react-router";
import { rethrowEntityRouteError } from "@/common/lib/errors/entity-route-error";
import type { RouteLoader } from "@/common/types/route-loader";
import { GetLedgerAccountsDocument } from "@/graphql/definitions";

export const accountLoader: RouteLoader<
  "/ledger/$ledgerOwner/$ledgerName/account/$accountName",
  { accountExists: true }
> = async ({ params, context, location }) => {
  const ledgerId = `${params.ledgerOwner}/${params.ledgerName}`;
  try {
    // Omitting status includes closed accounts and shares the sidebar cache.
    const { data } = await context.client.query({
      query: GetLedgerAccountsDocument,
      variables: { ledgerId },
      fetchPolicy: "cache-first",
    });
    // Hierarchy links also target derived ancestors, so retain those real
    // aggregate reports without accepting partial account-component prefixes.
    const exists = data?.getLedgerAccounts.some(
      (name) =>
        name === params.accountName ||
        name.startsWith(`${params.accountName}:`),
    );
    if (!exists) {
      throw notFound();
    }
    return { accountExists: true };
  } catch (error) {
    rethrowEntityRouteError(error, location);
  }
};
