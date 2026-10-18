import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { searchString } from "@/common/lib/search-params/tolerant";
import LedgerQueryPage from "@/features/bql/pages";
import { createLedgerHead } from "@/common/lib/seo/ledger-head";

const searchSchema = z.object({
  query: searchString(),
});

export const Route = createFileRoute("/ledger/$ledgerOwner/$ledgerName/query")({
  component: LedgerQueryPage,
  validateSearch: searchSchema,
  ssr: false,
  remountDeps: ({ params }) => ({
    ledgerOwner: params.ledgerOwner,
    ledgerName: params.ledgerName,
  }),
  head: (args) => createLedgerHead(args, "ledgerQuery", { noIndex: true }),
});
