import { notFound } from "@tanstack/react-router";
import type { RouterContext } from "@/common/types/router-context";
import { rethrowEntityRouteError } from "@/common/lib/errors/entity-route-error";
import { GetPullRequestDetailsDocument } from "@/graphql/definitions";

export async function loadPullRequestRoute({
  context,
  params,
  location,
}: {
  context: Pick<RouterContext, "client">;
  params: { ledgerOwner: string; ledgerName: string; prNumber: string };
  location: { href: string };
}) {
  const prNumber = Number(params.prNumber);
  if (
    !/^\d+$/.test(params.prNumber) ||
    !Number.isSafeInteger(prNumber) ||
    prNumber < 1 ||
    prNumber > 2_147_483_647
  ) {
    throw notFound();
  }

  try {
    const { data } = await context.client.query({
      query: GetPullRequestDetailsDocument,
      variables: {
        ledgerOwner: params.ledgerOwner,
        ledgerName: params.ledgerName,
        prNumber,
      },
      fetchPolicy: "cache-first",
    });
    if (!data?.getPullRequestDetails) throw notFound();
  } catch (error) {
    rethrowEntityRouteError(error, location);
  }
}
