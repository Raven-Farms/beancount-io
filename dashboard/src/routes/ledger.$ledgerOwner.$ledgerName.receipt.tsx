import { createFileRoute } from "@tanstack/react-router";
import ReceiptPage from "@/features/receipt/pages/receipt-page";
import { createLedgerHead } from "@/common/lib/seo/ledger-head";

export const Route = createFileRoute(
  "/ledger/$ledgerOwner/$ledgerName/receipt",
)({
  component: ReceiptPage,
  head: (args) => createLedgerHead(args, "ledgerReceipt", { noIndex: true }),
});
