import type { BeancountError, FileMap } from "@rustledger/wasm";

/** The engine's one-per-file summary of a syntax error: no file, no line. */
const LOAD_PARSE_SUMMARY = /^parse errors in /;

type LocatingModule = {
  parseMultiFile?: (
    files: FileMap,
    entryPoint: string,
  ) => { errors?: BeancountError[] } | BeancountError[];
};

/**
 * Replace the engine's located-nowhere "parse errors in main.bean" summaries
 * with the parse errors themselves, each with its file and line. A syntax
 * error in any file collapsed to one `LOAD` error per file with `file: null`
 * and `line: null`, so no client could show or jump to the bad line (w21/187).
 * `parseMultiFile` returns the same errors located (`P0012`, the file, line
 * and column); its messages lead with the file name, which is a field here.
 *
 * Errors stay as they were when there is no summary, when the module cannot
 * locate, or when it finds nothing to replace them with.
 */
export function locateParseErrors(
  errors: readonly BeancountError[],
  files: FileMap,
  entryPoint: string,
  engine: LocatingModule,
): BeancountError[] {
  const summaries = errors.filter(
    (error) => error.code === "LOAD" && LOAD_PARSE_SUMMARY.test(error.message),
  );
  if (summaries.length === 0 || typeof engine.parseMultiFile !== "function") {
    return [...errors];
  }
  let located: BeancountError[];
  try {
    const result = engine.parseMultiFile(files, entryPoint);
    located = (Array.isArray(result) ? result : (result.errors ?? [])).filter(
      (error) => error.severity === "error" && error.file !== null,
    );
  } catch {
    return [...errors];
  }
  if (located.length === 0) return [...errors];
  const rest = errors.filter((error) => !summaries.includes(error));
  const unprefixed = located.map((error) => ({
    ...error,
    message: error.file
      ? error.message.replace(`${error.file}: `, "")
      : error.message,
  }));
  return [...unprefixed, ...rest];
}
