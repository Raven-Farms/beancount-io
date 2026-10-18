import {
  createFileRoute,
  notFound,
  redirect,
  retainSearchParams,
} from "@tanstack/react-router";
import { CombinedGraphQLErrors } from "@apollo/client/errors";
import { LedgerLayout } from "@/common/components/ledger-layout";
import { LedgerRouteError } from "@/common/components/ledger-layout/ledger-route-error";
import { getSafeReturnPath } from "@/common/lib/auth/auth";
import { ledgerFilterSearchSchema } from "@/common/lib/ledger-search-params";
import { GetLedgerDocument } from "@/graphql/definitions";
import {
  LEDGER_OWNER_PATTERN,
  canonicalLedgerSlug,
} from "@/common/lib/beancount/ledger-name";

/** The same URL (still encoded) with the owner and name segments replaced. */
function ledgerHref(href: string, owner: string, name: string): string {
  const suffixAt = href.search(/[?#]/);
  const path = suffixAt === -1 ? href : href.slice(0, suffixAt);
  const suffix = suffixAt === -1 ? "" : href.slice(suffixAt);
  const [, root, , , ...rest] = path.split("/");
  return (
    [
      "",
      root,
      encodeURIComponent(owner),
      encodeURIComponent(name),
      ...rest,
    ].join("/") + suffix
  );
}

function ledgerAccessCode(error: unknown): string | undefined {
  if (!CombinedGraphQLErrors.is(error)) return undefined;
  for (const gqlError of error.errors) {
    const code = gqlError.extensions?.code;
    if (typeof code === "string") return code;
  }
  return undefined;
}

export const Route = createFileRoute("/ledger/$ledgerOwner/$ledgerName")({
  component: LedgerLayout,
  errorComponent: LedgerRouteError,
  validateSearch: (search) => ledgerFilterSearchSchema.parse(search),
  search: {
    // Keep account/filter/time across same-ledger report navigation (Related
    // Pages, sidebar). Explicit clears set the keys to undefined so retention
    // does not restore them. Ledger switches clear these in the switcher.
    middlewares: [retainSearchParams(["account", "filter", "time"])],
  },
  loader: async ({ params, context, location }) => {
    // Retyped and pasted links (`Example`, `example.git`) mean a real ledger:
    // send them to its URL. A name no ledger can have is simply not found,
    // never the "unexpected error" a refused read would otherwise become.
    const slug = canonicalLedgerSlug(params.ledgerName);
    if (!slug || !LEDGER_OWNER_PATTERN.test(params.ledgerOwner)) {
      throw notFound();
    }
    if (slug !== params.ledgerName) {
      throw redirect({
        href: ledgerHref(location.href, params.ledgerOwner, slug),
        statusCode: 301,
      });
    }
    const ledgerId = `${params.ledgerOwner}/${params.ledgerName}`;
    // Only the ledger itself gates the route: its failure (not found,
    // private) surfaces as the route error. Sidebar counts belong to the
    // panels that show them — DirectiveUsageIndicator owns its directive
    // count and renders nothing until the real number exists — so they never
    // delay primary content and never flash a false zero.
    //
    // Map known access denials to router redirect/notFound *before* the
    // SSR boundary: Seroval's ShallowErrorPlugin keeps only Error.message,
    // stripping Apollo's CombinedGraphQLErrors brand so the errorComponent
    // cannot classify UNAUTHENTICATED vs FORBIDDEN after hydration.
    let fullName: string | undefined;
    try {
      const { data } = await context.client.query({
        query: GetLedgerDocument,
        variables: { ledgerId },
      });
      fullName = data?.getLedger?.fullName;
    } catch (error) {
      const code = ledgerAccessCode(error);
      if (code === "UNAUTHENTICATED") {
        const next = getSafeReturnPath(location);
        throw redirect({
          to: "/auth/login",
          search: { next },
        });
      }
      // BAD_USER_INPUT: a slug the API refuses outright; nothing is there.
      if (
        code === "FORBIDDEN" ||
        code === "NOT_FOUND" ||
        code === "BAD_USER_INPUT"
      ) {
        throw notFound();
      }
      throw error;
    }
    // Owners match case-insensitively; one spelling is the ledger's address.
    const owner = fullName?.split("/")[0];
    if (
      owner &&
      owner !== params.ledgerOwner &&
      owner.toLowerCase() === params.ledgerOwner.toLowerCase()
    ) {
      throw redirect({
        href: ledgerHref(location.href, owner, params.ledgerName),
        statusCode: 301,
      });
    }
  },
});
