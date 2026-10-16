import { createFileRoute } from "@tanstack/react-router";
import LedgerAccountPage from "@/features/reports/account";
import { createLedgerHead } from "@/common/lib/seo/ledger-head";
import { accountJournalSearchSchema } from "@/features/reports/account/search";
import { accountLoader } from "@/features/reports/account/loader";
import { AccountNotFound } from "@/features/reports/account/not-found";

export const Route = createFileRoute(
  "/ledger/$ledgerOwner/$ledgerName/account/$accountName",
)({
  component: LedgerAccountPage,
  loader: accountLoader,
  notFoundComponent: AccountNotFound,
  validateSearch: (search) => accountJournalSearchSchema.parse(search),
  // A not-found boundary can retain the route's head snapshot. Only a
  // successful existence lookup may emit public account metadata.
  head: (args) =>
    args.loaderData?.accountExists &&
    args.match.status !== "error" &&
    args.match.status !== "notFound"
      ? createLedgerHead(args, "ledgerAccount")
      : { meta: [], links: [] },
});
