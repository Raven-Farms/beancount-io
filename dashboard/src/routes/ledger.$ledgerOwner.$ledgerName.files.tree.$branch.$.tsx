import { createFileRoute } from "@tanstack/react-router";
import LedgerDirectoryPage from "@/features/ledger-editor/directory-browse";
import { createLedgerHead } from "@/common/lib/seo/ledger-head";
import { requireSupportedBranch } from "@/features/ledger-editor/shared/lib/supported-branch";
import { BranchNotFound } from "@/features/ledger-editor/shared/components/branch-not-found";

export const Route = createFileRoute(
  "/ledger/$ledgerOwner/$ledgerName/files/tree/$branch/$",
)({
  component: LedgerDirectoryPage,
  beforeLoad: ({ params }) => requireSupportedBranch(params.branch),
  notFoundComponent: BranchNotFound,
  head: (args) =>
    args.match.status === "notFound"
      ? { meta: [], links: [] }
      : createLedgerHead(args, "ledgerFiles", { noIndex: true }),
});
