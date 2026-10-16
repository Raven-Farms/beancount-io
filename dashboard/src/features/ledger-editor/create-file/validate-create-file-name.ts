export type CreateFileNameIssue =
  | "empty"
  | "unsafe"
  | "emptySegment"
  | "git"
  | "exists"
  | null;

function createFilePathIssue(path: string): CreateFileNameIssue {
  if (
    typeof path !== "string" ||
    !path ||
    path.includes("\0") ||
    path.includes("\\")
  ) {
    return "unsafe";
  }
  for (const segment of path.split("/")) {
    if (segment === "") return "emptySegment";
    if (segment === "." || segment === "..") return "unsafe";
    if (segment.toLowerCase() === ".git") return "git";
  }
  return null;
}

/**
 * Reject empty paths, null bytes, backslashes, empty/`.`/`..` segments and
 * reserved `.git` segments. Ordinary nested paths remain allowed.
 */
export function isSafeCreateFilePath(path: string): boolean {
  return createFilePathIssue(path) === null;
}

/**
 * Whether `filename` (possibly nested under `dirPath`) collides with an
 * existing directory entry name at the create target.
 */
export function createFileNameCollides(
  filename: string,
  existingNames: ReadonlyArray<string>,
): boolean {
  const trimmed = filename.trim();
  if (!trimmed) return false;
  // Nested paths (a/b/c.bean) create into missing dirs; only collide when the
  // typed name is a single segment in the current directory listing.
  if (trimmed.includes("/")) {
    return false;
  }
  return existingNames.some((name) => name === trimmed);
}

export function createFileNameIssue(
  filename: string,
  existingNames: ReadonlyArray<string>,
  dirPath = "",
): CreateFileNameIssue {
  const trimmed = filename.trim();
  if (!trimmed) return "empty";
  const fullPath = dirPath ? `${dirPath}/${trimmed}` : trimmed;
  const pathIssue = createFilePathIssue(fullPath);
  if (pathIssue) return pathIssue;
  if (createFileNameCollides(trimmed, existingNames)) return "exists";
  return null;
}
