import { createFileRoute } from "@tanstack/react-router";
import LedgerFilePage from "@/features/ledger-editor/file-editor";
import { z } from "zod";
import {
  searchBoolean,
  searchPositiveInteger,
} from "@/common/lib/search-params/tolerant";
import { createLedgerHead } from "@/common/lib/seo/ledger-head";
import { fileLoader } from "@/features/ledger-editor/file-editor/loader";
import { FileNotFound } from "@/features/ledger-editor/file-editor/not-found";

const blobSearchSchema = z.object({
  editMode: searchBoolean(),
  lineNumber: searchPositiveInteger(),
});

export const Route = createFileRoute(
  "/ledger/$ledgerOwner/$ledgerName/files/blob/$branch/$",
)({
  component: LedgerFilePage,
  loader: fileLoader,
  notFoundComponent: FileNotFound,
  validateSearch: (search) => blobSearchSchema.parse(search),
  // A not-found boundary can keep the route's head snapshot; only a file
  // that loaded may describe itself.
  head: (args) =>
    args.match.status === "notFound" || args.match.status === "error"
      ? { meta: [], links: [] }
      : createLedgerHead(args, "ledgerFiles", {
          noIndex: Boolean(args.match.search.editMode),
        }),
});
