import { z } from "@/shared/zod-openapi-setup";
import { streamLedgerArchive } from "../archive-proxy";
import { ledgerIdOf, ledgerPathSchema } from "./schemas";
import { v1Route } from "@/server/rest/v1-route";
import { SAFE_ARCHIVE_NAME_PATTERN } from "../../../utils/safe-archive-name";

const archiveParamsSchema = ledgerPathSchema.extend({
  archive: z.string().regex(SAFE_ARCHIVE_NAME_PATTERN).openapi({
    description:
      "A Git reference (branch, tag, or commit) and its format: `<ref>.zip` or `<ref>.tar.gz`, as in `main.zip` or `main.tar.gz`. The name is passed to the repository unchanged.",
    example: "main.zip",
  }),
});

const archiveBodySchema = z.string().openapi({ format: "binary" });

/**
 * Authenticated archive download using the same identity seam as every other
 * v1 route. Browser navigation presents the session cookie; CLI and third-party
 * clients present an OAuth bearer token or personal API key.
 */
export const ARCHIVE_DOWNLOAD_ROUTES = [
  v1Route({
    method: "get",
    path: "/api-gateway/v1/ledgers/{owner}/{name}/archive/{archive}",
    summary: "Download a ledger archive",
    description:
      "Streams the archive for an authenticated caller with read access to the ledger. Send a session cookie, OAuth bearer token, or personal API key.",
    params: archiveParamsSchema,
    responses: {
      200: {
        description:
          "The archive bytes, with the repository's own `Content-Type` (`application/octet-stream` for both formats today) and an attachment `Content-Disposition`",
        content: {
          "application/octet-stream": { schema: archiveBodySchema },
          "application/zip": { schema: archiveBodySchema },
          "application/gzip": { schema: archiveBodySchema },
        },
      },
    },
    handler: async ({ layers }, { identity, params, ctx }) => {
      const ledgerId = ledgerIdOf(params);
      await streamLedgerArchive(ctx, layers, {
        ledgerId,
        archive: params.archive,
        identity,
      });
      return undefined;
    },
  }),
] as const;
