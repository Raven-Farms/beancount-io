import { isBeancountFile } from "../../common/ledger-file-types";

/** Why a typed name can't be created, or the name it creates. */
export type LedgerFileNameCheck =
  | { ok: true; filename: string }
  | {
      ok: false;
      issue: "empty" | "path" | "extension" | "exists";
      filename?: string;
    };

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
  const named = last.includes(".") ? last : `${last}.bean`;
  if (/^\.(bean|beancount)$/i.test(named) || !isBeancountFile(named)) {
    return { ok: false, issue: "extension" };
  }
  const filename = [...segments.slice(0, -1), named].join("/");
  if (existingNames.includes(filename)) {
    return { ok: false, issue: "exists", filename };
  }
  return { ok: true, filename };
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
