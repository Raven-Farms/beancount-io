import { createFileRoute, redirect } from "@tanstack/react-router";
import { z } from "zod";
import { searchString } from "@/common/lib/search-params/tolerant";

/**
 * Backward compatibility route for old query-based create file URLs
 * Redirects to new GitHub-style path-based URLs
 *
 * Old format: /files/create?dirPath=accounts
 * New format: /files/new/main/accounts
 */

// Define search schema for backward compatibility
const searchSchema = z.object({
  dirPath: searchString().transform((dirPath) => dirPath ?? ""),
});

export const Route = createFileRoute(
  "/ledger/$ledgerOwner/$ledgerName/files/create",
)({
  validateSearch: searchSchema,
  beforeLoad: ({ params, search }) => {
    const { ledgerOwner, ledgerName } = params;
    const dirPath = search.dirPath || "";

    throw redirect({
      to: "/ledger/$ledgerOwner/$ledgerName/files/new/$branch/$",
      params: {
        ledgerOwner,
        ledgerName,
        branch: "main",
        _splat: dirPath,
      },
    });
  },
});
