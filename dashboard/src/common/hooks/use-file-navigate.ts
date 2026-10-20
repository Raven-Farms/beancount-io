import { decodeLedgerId } from "@/common/lib/utils/encode.ts";
import { useNavigate } from "@tanstack/react-router";

/** Canonical Files browser root (matches the sidebar and registered tree route). */
export function getLedgerFilesRootPath(
  ledgerOwner: string,
  ledgerName: string,
  branch = "main",
): string {
  return `/ledger/${ledgerOwner}/${ledgerName}/files/tree/${branch}`;
}

/** Canonical file view URL for a ledger path, each segment encoded. */
export function getLedgerFileBlobPath(
  ledgerId: string,
  path: string,
  suffix = "",
): string {
  const { ledgerOwner, ledgerName } = decodeLedgerId(ledgerId);
  const encoded = path.split("/").map(encodeURIComponent).join("/");
  return `/ledger/${ledgerOwner}/${ledgerName}/files/blob/main/${encoded}${suffix}`;
}

/**
 * Hook for navigating to files and directories using GitHub-style URLs
 *
 * @example
 * // Navigate to a file
 * fileNavigate(ledgerId, "file", "main.bean", { editMode: true, lineNumber: 42 })
 * // Result: /ledger/owner/name/files/blob/main/main.bean?editMode=true&lineNumber=42
 *
 * // Navigate to a directory
 * fileNavigate(ledgerId, "dir", "accounts")
 * // Result: /ledger/owner/name/files/tree/main/accounts
 */
export const useFileNavigate = () => {
  const navigate = useNavigate();
  return (
    ledgerId: string,
    type: "file" | "dir",
    path: string,
    options?: {
      lineNumber?: number;
      editMode?: boolean;
    },
  ) => {
    const { lineNumber, editMode } = options || {};
    const { ledgerOwner, ledgerName } = decodeLedgerId(ledgerId);

    // Hardcode branch as "main" for now (future: support multiple branches)
    const branch = "main";

    if (type === "file") {
      void navigate({
        to: "/ledger/$ledgerOwner/$ledgerName/files/blob/$branch/$",
        params: {
          ledgerOwner,
          ledgerName,
          branch,
          _splat: path, // TanStack Router uses "_splat" as the key for splat parameters
        },
        search: { editMode, lineNumber },
      });
    } else {
      void navigate({
        to: "/ledger/$ledgerOwner/$ledgerName/files/tree/$branch/$",
        params: {
          ledgerOwner,
          ledgerName,
          branch,
          _splat: path, // TanStack Router uses "_splat" as the key for splat parameters
        },
      });
    }
  };
};
