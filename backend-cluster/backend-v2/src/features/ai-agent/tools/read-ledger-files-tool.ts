import { tool } from "ai";
import { z } from "zod";
import { logger } from "@/shared/logger";
import { BadUserInputError } from "@/shared/errors";
import type { ToolContext } from "./types";
import { toolOutputSchema } from "./types";
import { runToolSafely } from "../utils/run-tool";
import { normalizeAgentRepoPath } from "./agent-repo-path";

const toolLogger = logger.child({ module: "tool:read-ledger-file" });

export const description =
  "Read one or more beancount ledger files in a single call. `content` is raw text; the 1-based " +
  "startLine/endLine it spans and the file's totalLines come alongside it, not in the text. " +
  "Use start_line/end_line per file to limit tokens for large files. A file that is not valid UTF-8 " +
  "comes back with `lossy: true`: its undecodable bytes read as U+FFFD, and edits to it are refused.";

export const readLedgerFilesInputSchema = z.object({
  files: z
    .array(
      z.object({
        path: z
          .string()
          .describe("File path within the ledger repo, e.g. 'main.bean'"),
        start_line: z
          .number()
          .int()
          .min(1)
          .optional()
          .describe("First line to return (1-based). Default: 1"),
        end_line: z
          .number()
          .int()
          .min(1)
          .optional()
          .describe("Last line to return (inclusive). Default: end of file"),
      }),
    )
    .min(1)
    .describe(
      "One or more files to read. Each entry may limit to a line range.",
    ),
});

const readLedgerFileSectionSchema = z.object({
  path: z.string(),
  startLine: z.number().int(),
  endLine: z.number().int(),
  totalLines: z.number().int(),
  content: z.string(),
  sha: z
    .string()
    .describe(
      "The file's blob SHA; pass it to updateLedgerFiles content or deleteLedgerFiles to refuse the write if the file changed since.",
    ),
  lossy: z
    .literal(true)
    .optional()
    .describe(
      "Present when the file is not valid UTF-8: `content` shows U+FFFD for its undecodable bytes.",
    ),
});
type ReadLedgerFileSection = z.infer<typeof readLedgerFileSectionSchema>;

export const readLedgerFilesOutputSchema = toolOutputSchema(
  z.array(readLedgerFileSectionSchema),
);
export type ReadLedgerFilesOutput = z.infer<typeof readLedgerFilesOutputSchema>;

export async function executeReadLedgerFiles(
  ctx: Pick<ToolContext, "services" | "identity" | "ledgerId">,
  input: { files: { path: string; start_line?: number; end_line?: number }[] },
): Promise<ReadLedgerFilesOutput> {
  const { services, identity, ledgerId } = ctx;
  toolLogger.debug("Reading ledger files", { count: input.files.length });
  return runToolSafely({
    logger: toolLogger,
    message: "Failed to read files",
    execute: async (): Promise<ReadLedgerFileSection[]> => {
      const requestedFiles = input.files.map((file) => ({
        ...file,
        path: normalizeAgentRepoPath(file.path),
      }));
      // A reversed range is wrong whatever the file holds, so it is refused
      // before anything is read.
      for (const { path, start_line, end_line } of requestedFiles) {
        if (
          start_line !== undefined &&
          end_line !== undefined &&
          start_line > end_line
        ) {
          throw new BadUserInputError(
            `${path}: start_line ${start_line} is after end_line ${end_line}`,
            "start_line",
            "Pass start_line ≤ end_line, or omit either to read from the start or to the end of the file.",
          );
        }
      }
      const files = await services.ledgerRepo.getFilesContent({
        ledgerId,
        identity,
        paths: requestedFiles.map((file) => file.path),
      });
      const fileMap = new Map(files.map((f) => [f.path, f]));

      const sections: ReadLedgerFileSection[] = [];

      for (const { path, start_line, end_line } of requestedFiles) {
        const file = fileMap.get(path);
        if (file === undefined) {
          throw new Error(`file not found: ${path}`);
        }
        const raw = file.content;
        // A trailing newline ends the last line; it does not start another,
        // so the count matches `wc -l` and every editor (w23/005).
        const terminated = raw.endsWith("\n");
        const lines = (terminated ? raw.slice(0, -1) : raw).split("\n");
        // A start past the last line used to come back as an empty section
        // whose own metadata contradicted itself (startLine 10, endLine 9).
        // An end_line past the end is still clamped: "up to N lines" is an
        // ordinary request against a file whose length the caller cannot know.
        if (start_line !== undefined && start_line > lines.length) {
          throw new BadUserInputError(
            `${path}: start_line ${start_line} is past the end of the file (${lines.length} lines)`,
            "start_line",
            `Pass a start_line between 1 and ${lines.length}.`,
          );
        }
        const s = (start_line ?? 1) - 1;
        const e = end_line ?? lines.length;
        const slice = lines.slice(s, e);
        const reachesEnd = s + slice.length === lines.length;
        sections.push({
          path,
          startLine: s + 1,
          endLine: s + slice.length,
          totalLines: lines.length,
          // The terminator goes back on when the slice reaches the end, so a
          // whole-file read is still the file byte for byte.
          content: slice.join("\n") + (terminated && reachesEnd ? "\n" : ""),
          sha: file.sha,
          ...(file.lossy && { lossy: true as const }),
        });
      }

      return sections;
    },
  });
}

export function createReadLedgerFilesTool(ctx: ToolContext) {
  return tool({
    description,
    inputSchema: readLedgerFilesInputSchema,
    outputSchema: readLedgerFilesOutputSchema,
    execute: (input) =>
      executeReadLedgerFiles(
        {
          services: ctx.services,
          identity: ctx.identity,
          ledgerId: ctx.ledgerId,
        },
        input,
      ),
  });
}
