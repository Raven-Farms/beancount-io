import { DomainError, ErrorCategory, NotFoundError } from "@/shared/errors";

/**
 * A directory listing that cannot be mistaken for an empty directory
 * (w23/014). Shared by the repo service (REST `files`, MCP `listLedgerFiles`)
 * and the workflow (GraphQL `getLedgerDirContent`).
 *
 * Git stores no empty directories, so below the repository root an empty
 * listing means the path does not exist, and the ledger's 404 means it names
 * a file. Both used to read as an empty directory or an unnamed resource, so
 * an agent that misspelled `Imports` was told it was empty and could create a
 * duplicate tree. The root of an empty repository still lists as `[]`.
 */
export async function listDirectory<T>(
  dirPath: string | null | undefined,
  list: () => Promise<readonly T[]>,
): Promise<readonly T[]> {
  const named = dirPath?.replace(/^\/+|\/+$/g, "") || undefined;
  const entries = await list().catch((error: unknown) => {
    if (
      named !== undefined &&
      error instanceof DomainError &&
      error.category === ErrorCategory.NOT_FOUND
    ) {
      throw new NotFoundError(
        `Directory '${named}'`,
        undefined,
        `'${named}' is a file, not a directory: read it with readLedgerFiles, or list its parent directory.`,
      );
    }
    throw error;
  });
  if (named !== undefined && entries.length === 0) {
    throw new NotFoundError(
      `Directory '${named}'`,
      undefined,
      "List its parent directory (or omit the path for the repository root) to see what exists; names are case-sensitive.",
    );
  }
  return entries;
}
