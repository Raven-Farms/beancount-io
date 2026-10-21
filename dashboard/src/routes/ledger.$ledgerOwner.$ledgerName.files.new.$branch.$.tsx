import { createFileRoute } from "@tanstack/react-router";
import LedgerCreateFilesPage from "@/features/ledger-editor/create-file";
import { createLedgerHead } from "@/common/lib/seo/ledger-head";
import { requireSupportedBranch } from "@/features/ledger-editor/shared/lib/supported-branch";
import { BranchNotFound } from "@/features/ledger-editor/shared/components/branch-not-found";

export const Route = createFileRoute(
  "/ledger/$ledgerOwner/$ledgerName/files/new/$branch/$",
)({
  component: LedgerCreateFilesPage,
  // Creating here would write to main under another branch's name.
  beforeLoad: ({ params }) => requireSupportedBranch(params.branch),
  notFoundComponent: BranchNotFound,
  head: (args) =>
    args.match.status === "notFound"
      ? { meta: [], links: [] }
      : createLedgerHead(args, "ledgerFilesCreate", { noIndex: true }),
});
