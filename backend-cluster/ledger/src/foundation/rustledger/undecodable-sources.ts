import type { BeancountError, FileMap } from "@rustledger/wasm";
import { collectSourceFiles, UNDECODABLE_SOURCE } from "./file-map-loader";

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
