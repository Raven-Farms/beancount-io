import { createFileRoute } from "@tanstack/react-router";
import EntryPage from "@/features/journal/pages/entry-page";
import { createLedgerHead } from "@/common/lib/seo/ledger-head";
import { loadEntryRoute } from "@/features/journal/loaders/entry-loader";

export const Route = createFileRoute(
  "/ledger/$ledgerOwner/$ledgerName/entry/$entryHash",
)({
  component: EntryPage,
  loader: loadEntryRoute,
  head: (args) => createLedgerHead(args, "ledgerEntry"),
});
