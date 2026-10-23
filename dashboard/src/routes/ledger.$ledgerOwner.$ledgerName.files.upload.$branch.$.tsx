import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import LedgerUploadFilesPage from "@/features/ledger-editor/upload-files";
import { createLedgerHead } from "@/common/lib/seo/ledger-head";
import { requireSupportedBranch } from "@/features/ledger-editor/shared/lib/supported-branch";
import { BranchNotFound } from "@/features/ledger-editor/shared/components/branch-not-found";

// Empty search schema - this route uses path params only
const searchSchema = z.object({});

export const Route = createFileRoute(
  "/ledger/$ledgerOwner/$ledgerName/files/upload/$branch/$",
)({
  component: LedgerUploadFilesPage,
  validateSearch: (search) => searchSchema.parse(search),
  // Uploading here would write to main under another branch's name.
  beforeLoad: ({ params }) => requireSupportedBranch(params.branch),
  notFoundComponent: BranchNotFound,
  head: (args) =>
    args.match.status === "notFound"
      ? { meta: [], links: [] }
      : createLedgerHead(args, "ledgerFilesUpload", { noIndex: true }),
});
