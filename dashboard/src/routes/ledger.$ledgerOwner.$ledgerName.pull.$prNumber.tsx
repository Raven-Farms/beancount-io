import { createFileRoute } from "@tanstack/react-router";
import PRReviewPage from "@/features/git/pull-requests/pages/pr-review-page";
import { createLedgerHead } from "@/common/lib/seo/ledger-head";
import { loadPullRequestRoute } from "@/features/git/pull-requests/loaders/pull-request-loader";

export const Route = createFileRoute(
  "/ledger/$ledgerOwner/$ledgerName/pull/$prNumber",
)({
  component: PRReviewPage,
  loader: loadPullRequestRoute,
  head: (args) => createLedgerHead(args, "ledgerPullRequest"),
});
