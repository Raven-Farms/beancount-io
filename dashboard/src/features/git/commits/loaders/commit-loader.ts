import { notFound } from "@tanstack/react-router";
import type { RouterContext } from "@/common/types/router-context";
import { rethrowEntityRouteError } from "@/common/lib/errors/entity-route-error";
import { GetCommitDetailsDocument } from "@/graphql/definitions";

export async function loadCommitRoute({
  context,
  params,
  location,
}: {
  context: Pick<RouterContext, "client">;
  params: { ledgerOwner: string; ledgerName: string; commitSha: string };
  location: { href: string };
}) {
  try {
    const { data } = await context.client.query({
      query: GetCommitDetailsDocument,
      variables: {
        ledgerId: `${params.ledgerOwner}/${params.ledgerName}`,
        sha: params.commitSha,
      },
      fetchPolicy: "cache-first",
    });
    if (!data?.getCommitDetails) throw notFound();
  } catch (error) {
    rethrowEntityRouteError(error, location);
  }
}
