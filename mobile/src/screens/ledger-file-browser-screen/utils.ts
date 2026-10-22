import { isBeancountFile } from "../../common/ledger-file-types";
import { isLedgerGone } from "../../common/graphql-error-codes";

/** Why a typed name can't be created, or the name it creates. */
export type LedgerFileNameCheck =
  | { ok: true; filename: string }
  | {
      ok: false;
      issue: "empty" | "path" | "extension" | "exists";
      filename?: string;
    };

/**
 * Extensions of files that are not ledgers: typed on a new file they are a
 * mistake to name, not a word of the name. Any other suffix ("Mr.Smith",
 * "acme.inc", "budget.march") is part of it.
 */
const OTHER_EXTENSIONS = new Set(
  (
    "txt text csv tsv md markdown json yaml yml toml xml html htm ini log " +
    "py js ts sh sql pdf doc docx xls xlsx ods odt rtf zip png jpg jpeg gif " +
    "ofx qif qfx"
  ).split(" "),
);

/**
 * The name with `.bean` added unless it already carries an extension. Only a
 * known non-ledger extension reads as one ("notes.txt", which the check then
 * refuses): a dot inside a name ("2024.q1", "Mr.Smith", "Jan. expenses") is
 * part of it, and the dialog promises `.bean` to a name with no extension
 * (w21/275, w21/429).
 */
function withBeanExtension(name: string): string {
  const dot = name.lastIndexOf(".");
  if (dot < 0) return `${name}.bean`;
  if (isBeancountFile(name)) return name;
  const suffix = name.slice(dot + 1);
  if (suffix === "") return `${name}bean`;
  return OTHER_EXTENSIONS.has(suffix.toLowerCase()) ? name : `${name}.bean`;
}

/**
 * Check a typed new-file name. A relative path into folders (`sub/notes`)
 * is allowed, as the server and the dashboard allow it (w3/196): each segment
 * must be non-empty and not `.` or `..`, and backslashes and control
 * characters are refused. A last segment with no extension gets `.bean`.
 * Each refusal says which rule it broke so the dialog can name it (w21/014).
 */
export function checkLedgerFileName(
  input: string,
  existingNames: readonly string[] = [],
): LedgerFileNameCheck {
  const trimmed = input.trim();
  if (!trimmed) return { ok: false, issue: "empty" };
  const segments = trimmed.split("/");
  if (
    trimmed.includes("\\") ||
    /[\u0000-\u001f]/.test(trimmed) ||
    segments.some(
      (segment) => segment === "" || segment === "." || segment === "..",
    )
  ) {
    return { ok: false, issue: "path" };
  }
  const last = segments[segments.length - 1]!;
  const named = withBeanExtension(last);
  if (/^\.(bean|beancount)$/i.test(named) || !isBeancountFile(named)) {
    return { ok: false, issue: "extension" };
  }
  const filename = [...segments.slice(0, -1), named].join("/");
  if (existingNames.includes(filename)) {
    return { ok: false, issue: "exists", filename };
  }
  return { ok: true, filename };
}

/**
 * Whether a listing of the folder a new file targets already holds it. The
 * name check only sees the current folder, so `sub/notes` passed at the root
 * even when `sub/notes.bean` existed, and the server refused the create after
 * the dialog had closed (w21/222).
 */
export function listingHasFile(
  entries: readonly { path: string; type: string }[],
  filePath: string,
): boolean {
  const wanted = filePath.replace(/^\/+/, "");
  return entries.some(
    (entry) =>
      entry.type !== "dir" && entry.path.replace(/^\/+/, "") === wanted,
  );
}

/** The folder part of a relative path, or "" at the root. */
export function parentDirectory(path: string): string {
  const slash = path.replace(/\/+$/, "").lastIndexOf("/");
  return slash < 0 ? "" : path.slice(0, slash);
}

export function normalizeLedgerFileName(input: string): string | null {
  const check = checkLedgerFileName(input);
  return check.ok ? check.filename : null;
}

export function buildLedgerFilePath(
  directory: string,
  filename: string,
): string {
  const cleanDirectory = directory.replace(/^\/+|\/+$/g, "");
  return cleanDirectory ? `${cleanDirectory}/${filename}` : filename;
}

/**
 * Whether Files offers Delete for the file at `path`. Only the ledger's root
 * `main.bean` is protected, as the server's `deleteLedgerFile` rule is; a
 * folder's own `main.bean` used to be locked too because the bare name was
 * compared (w21/049, the dashboard's w3/626).
 */
export function canDeleteLedgerFile(path: string): boolean {
  return path.replace(/^\/+/, "") !== "main.bean";
}

type Entry = { name: string; type: string; path: string };

export function sortEntries<T extends Entry>(entries: T[]): T[] {
  return [...entries].sort((a, b) => {
    if (a.type === "dir" && b.type !== "dir") return -1;
    if (a.type !== "dir" && b.type === "dir") return 1;
    return a.name.localeCompare(b.name);
  });
}

/** A directory stack together with the ledger it was built in. */
export type LedgerPathStack = { ledgerId: string; stack: string[] };

/**
 * The stack to browse with. One from another ledger starts over at the root:
 * the Files tab stays mounted across a ledger switch, and a folder remembered
 * from the previous ledger would list as empty and aim Create file at a path
 * the new ledger never had.
 */
export function pathStackForLedger(
  state: LedgerPathStack,
  ledgerId: string,
): string[] {
  return state.ledgerId === ledgerId ? state.stack : [""];
}

export function pushPathStack(stack: string[], path: string): string[] {
  return [...stack, path];
}

export function popPathStack(stack: string[]): string[] {
  if (stack.length <= 1) return stack;
  return stack.slice(0, -1);
}

/**
 * Whether a listing failed because its folder no longer exists. Git keeps no
 * empty folders, so deleting a folder's last file removes the folder, and the
 * listing then answers NOT_FOUND; the browser read that as "Failed to load"
 * and pull to refresh could not clear it (w21/088). The root is never "gone":
 * a NOT_FOUND there is the ledger's, which the ledger guard reports.
 */
export function isFolderGone(error: unknown, stack: string[]): boolean {
  return stack.length > 1 && isLedgerGone(error);
}

/**
 * Whether deleting one row leaves its folder empty, and so removes it. The
 * browser steps up before refreshing rather than list a folder that is gone.
 */
export function deleteEmptiesFolder(
  stack: string[],
  rowsInFolder: number,
): boolean {
  return stack.length > 1 && rowsInFolder === 1;
}
