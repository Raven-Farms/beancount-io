import type { BeancountError, FileMap } from "@rustledger/wasm";
import {
  collectSourceFiles,
  isHiddenRepoPath,
  UNDECODABLE_SOURCE,
} from "./file-map-loader";

/**
 * The files the engine parses: undecodable sources read as empty files, and a
 * hidden file no include reaches is left out, since the engine's glob matches
 * `y/.draft.bean` for `include "y/*.bean"` where Beancount's skips it (w21/657).
 */
export function parseableFiles(files: FileMap, entryPoint: string): FileMap {
  const undecodable = Object.values(files).includes(UNDECODABLE_SOURCE);
  const hidden = Object.keys(files).some(isHiddenRepoPath);
  if (!undecodable && !hidden) return files;
  const reached = hidden
    ? new Set(collectSourceFiles(files, entryPoint))
    : undefined;
  const parseable = Object.create(null) as FileMap;
  for (const [path, content] of Object.entries(files)) {
    if (reached && !reached.has(path) && isHiddenRepoPath(path)) continue;
    parseable[path] = content === UNDECODABLE_SOURCE ? "" : content;
  }
  return parseable;
}

/** One error per undecodable file the entry point's includes reach. */
export function reportUndecodableSources(
  errors: BeancountError[],
  files: FileMap,
  entryPoint: string,
): BeancountError[] {
  if (!Object.values(files).includes(UNDECODABLE_SOURCE)) return errors;
  const reached = collectSourceFiles(files, entryPoint).filter(
    (path) => files[path] === UNDECODABLE_SOURCE,
  );
  if (reached.length === 0) return errors;
  return [
    ...errors,
    ...reached.map((path): BeancountError => ({
      message: `${path} is not UTF-8 text (invalid UTF-8 or binary data), so none of its entries were read`,
      code: "INVALID_UTF8",
      phase: "parse",
      hint: "Re-save the file as UTF-8, or remove the include that reaches it.",
      file: path,
      line: 1,
      column: null,
      end_line: null,
      end_column: null,
      severity: "error",
    })),
  ];
}
