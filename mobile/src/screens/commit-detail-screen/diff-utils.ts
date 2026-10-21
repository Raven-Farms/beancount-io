type DiffLineType = "added" | "removed" | "context";

export type DiffLine = {
  type: DiffLineType;
  content: string;
};

/**
 * Classify each line of a unified diff by where it sits, not by prefix alone.
 * Inside a hunk a `+`/`-` always marks content, even when the content starts
 * with `++`/`--` (deleting a `---` line emits `----`). The `--- a/file` and
 * `+++ b/file` headers only appear between `diff --git` and the first `@@`.
 */
export function parseDiff(diff: string): DiffLine[] {
  let inHunk = false;
  return diff.split("\n").map((line): DiffLine => {
    if (line.startsWith("diff --git")) {
      inHunk = false;
    } else if (line.startsWith("@@")) {
      inHunk = true;
    } else if (inHunk && line.startsWith("+")) {
      return { type: "added", content: line };
    } else if (inHunk && line.startsWith("-")) {
      return { type: "removed", content: line };
    }
    return { type: "context", content: line };
  });
}

type CommitFileStatus = "added" | "removed" | "modified" | "renamed";

export type CommitFileRow = {
  filename: string;
  additions: number;
  deletions: number;
  status: CommitFileStatus;
  /** The path before a rename; null otherwise. */
  previousFilename: string | null;
};

/**
 * What the commit did to each file, read from the diff's extended headers:
 * `new file mode`, `deleted file mode` and a rename's `rename from`/`rename
 * to`. They are there even for an empty file, whose diff has no hunk. Keyed
 * by the (new) path.
 */
function fileHeaders(
  diff: string,
): Map<string, Pick<CommitFileRow, "status" | "previousFilename">> {
  const headers = new Map<
    string,
    Pick<CommitFileRow, "status" | "previousFilename">
  >();
  let current: Pick<CommitFileRow, "status" | "previousFilename"> | null = null;
  let path = "";
  let inHunk = false;
  for (const line of diff.split("\n")) {
    if (line.startsWith("diff --git ")) {
      // `a/<p> b/<p>`: the two halves agree unless the file was renamed, and
      // then `rename to` names the new path.
      const rest = line.slice("diff --git a/".length);
      const half = (rest.length - 3) / 2;
      path = Number.isInteger(half) ? rest.slice(0, half) : rest;
      current = { status: "modified", previousFilename: null };
      headers.set(path, current);
      inHunk = false;
    } else if (!current || inHunk) {
      continue;
    } else if (line.startsWith("@@")) {
      inHunk = true;
    } else if (line.startsWith("new file mode")) {
      current.status = "added";
    } else if (line.startsWith("deleted file mode")) {
      current.status = "removed";
    } else if (line.startsWith("rename from ")) {
      current.status = "renamed";
      current.previousFilename = line.slice("rename from ".length);
    } else if (line.startsWith("rename to ")) {
      headers.delete(path);
      path = line.slice("rename to ".length);
      headers.set(path, current);
    }
  }
  return headers;
}

/**
 * The commit's FILES rows. The server lists a rename as the old path plus the
 * new one, each with no line counts, and gives no status, so a rename read as
 * two untouched files and a created empty file looked like a deleted one
 * (w21/132). The diff the screen already reads says what happened.
 */
export function commitFileRows(
  files: readonly { filename: string; additions: number; deletions: number }[],
  diff: string | null | undefined,
): CommitFileRow[] {
  const headers = fileHeaders(diff ?? "");
  const renamedFrom = new Set(
    [...headers.values()].flatMap((h) =>
      h.previousFilename ? [h.previousFilename] : [],
    ),
  );
  return files.flatMap((file) => {
    const header = headers.get(file.filename);
    if (!header && renamedFrom.has(file.filename)) return [];
    return [
      {
        ...file,
        status: header?.status ?? "modified",
        previousFilename: header?.previousFilename ?? null,
      },
    ];
  });
}
