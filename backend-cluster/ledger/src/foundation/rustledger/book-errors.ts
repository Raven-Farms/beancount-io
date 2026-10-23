import type { BeancountError } from "@rustledger/wasm";

/**
 * Put booking and interpolation errors on the transaction they are about.
 *
 * The engine reports `BOOK` errors ("interpolation failed: cannot infer
 * currency for posting to account Assets:Cash (2026-01-05, "narration")") with
 * no file or line, so the app could not open them and the file editor's banner,
 * which matches by file, never listed them. The message ends with the entry's
 * date and narration: the transaction whose first line has that date and ends
 * its strings with that narration is the one. Several transactions sharing both
 * are told apart by order, as the engine reports them in the order it books
 * them; when the counts of errors and transactions differ the error is left as
 * it was (w21/534).
 */

const BOOK_ENTRY = /\((\d{4}-\d{2}-\d{2}), "((?:[^"\\]|\\.)*)"\)$/u;
const TRANSACTION_LINE = /^(\d{4}-\d{2}-\d{2})\s+(?:[*!]|txn)(\s|$)/u;
const QUOTED = /"((?:[^"\\]|\\.)*)"/gu;

type Block = { file: string; line: number };

const unescape = (text: string): string => text.replace(/\\(.)/gu, "$1");

/** Every transaction's first line, keyed by its date and last quoted string. */
function transactionLines(
  files: Readonly<Record<string, string>>,
  entryPoint: string,
): Map<string, Block[]> {
  const found = new Map<string, Block[]>();
  const names = [
    entryPoint,
    ...Object.keys(files)
      .filter((name) => name !== entryPoint)
      .sort(),
  ];
  for (const file of names) {
    const content = files[file];
    if (content === undefined) continue;
    content.split(/\r\n|\n|\r/u).forEach((text, index) => {
      const head = TRANSACTION_LINE.exec(text);
      if (!head) return;
      const strings = [...text.matchAll(QUOTED)];
      const last = strings[strings.length - 1];
      if (!last) return;
      const key = `${head[1]}\u0000${unescape(last[1])}`;
      const list = found.get(key) ?? [];
      list.push({ file, line: index + 1 });
      found.set(key, list);
    });
  }
  return found;
}

export function locateBookErrors(
  errors: readonly BeancountError[],
  files: Readonly<Record<string, string>>,
  entryPoint: string,
): BeancountError[] {
  const wanted = (error: BeancountError) =>
    error.code === "BOOK" && !error.file ? BOOK_ENTRY.exec(error.message.trim()) : null;
  if (!errors.some(wanted)) return [...errors];

  const blocks = transactionLines(files, entryPoint);
  const keyOf = (match: RegExpExecArray) =>
    `${match[1]}\u0000${unescape(match[2])}`;
  const errorCounts = new Map<string, number>();
  for (const error of errors) {
    const match = wanted(error);
    if (match) {
      errorCounts.set(keyOf(match), (errorCounts.get(keyOf(match)) ?? 0) + 1);
    }
  }
  const seen = new Map<string, number>();
  return errors.map((error) => {
    const match = wanted(error);
    if (!match) return error;
    const key = keyOf(match);
    const candidates = blocks.get(key);
    if (!candidates || candidates.length !== errorCounts.get(key)) return error;
    const n = seen.get(key) ?? 0;
    seen.set(key, n + 1);
    const at = candidates[n];
    return { ...error, file: at.file, line: at.line, column: error.column ?? 1 };
  });
}
