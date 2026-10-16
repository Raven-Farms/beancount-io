import { createFileRoute } from "@tanstack/react-router";
import CommitDetailPage from "@/features/git/commits/pages/commit-detail-page";
import { createLedgerHead } from "@/common/lib/seo/ledger-head";
import { loadCommitRoute } from "@/features/git/commits/loaders/commit-loader";

export const Route = createFileRoute(
  "/ledger/$ledgerOwner/$ledgerName/commit/$commitSha",
)({
  component: CommitDetailPage,
  loader: loadCommitRoute,
  head: (args) => createLedgerHead(args, "ledgerCommit"),
});
