const HEADER = /^(\d{4}-\d{2}-\d{2})\s+(\S+)\s*(.*)$/;
const FLAG = /^(txn|[*!#?%&A-Z])$/;
const QUOTED = /^"((?:[^"\\]|\\.)*)"\s*/;

/**
 * A written string as the entry shows it: Beancount's `\"` and `\\` read
 * back. Any other escape is not judged (null), so an ordinary entry keeps its
 * Edit and Delete; skipping every string with a backslash left the first copy
 * of an escaped narration deletable (w21/504).
 */
function unescapeWritten(written: string): string | null {
  if (/\\[^"\\]/.test(written.replace(/\\\\/g, ""))) return null;
  return written.replace(/\\(["\\])/g, "$1");
}

/**
 * The transaction header a source slice opens with: its day and quoted
 * strings. A narration may continue onto the next line, so the strings are
 * read across lines until each closes, and the old `"Payee" | "Narration"`
 * form's bar is skipped (w21/505). A string that never closes leaves the
 * header unread (null), so the entry is not judged.
 */
function sliceHeader(slice: string): {
  date: string;
  strings: string[];
} | null {
  const lines = slice.split("\n");
  const first = lines.findIndex(
    (text) => text.trim() !== "" && !text.trim().startsWith(";"),
  );
  const header = first < 0 ? null : HEADER.exec(lines[first]!.trim());
  // A slice that opens with `pad`, `balance`, … is not this transaction's text.
  if (!header || !FLAG.test(header[2]!)) return null;
  const strings: string[] = [];
  let rest = [header[3]!, ...lines.slice(first + 1)].join("\n");
  for (;;) {
    rest = rest.replace(/^\s*\|?\s*/, "");
    const match = QUOTED.exec(rest);
    if (!match) break;
    strings.push(match[1]!);
    rest = rest.slice(match[0].length);
  }
  if (rest.startsWith('"')) return null;
  return { date: header[1]!, strings };
}

/**
 * Whether the entry shown is not the text its source slice holds: a copy that
 * `amortize_over` or `forecast` generated from another entry. A copy answers
 * with its source's slice and checksum, so deleting or editing "it" removes or
 * rewrites the source and every other copy (w21/443). The ledger names the
 * source on newer servers (`generated_from`); until then the copy gives itself
 * away by a day or a name its source's first line does not carry.
 *
 * Conservative: a slice that cannot be read, or a string with an escape other than a quote or backslash, is not
 * judged, so an ordinary entry keeps its Edit and Delete.
 */
export function isPluginCopy(
  entry: { date: string; payee?: string | null; narration?: string | null },
  slice: string | null | undefined,
): boolean {
  if (!slice) return false;
  const header = sliceHeader(slice);
  if (!header) return slice.trim() !== "" && sliceOpensAnotherKind(slice);
  if (entry.date.slice(0, 10) !== header.date) return true;
  const [payee, narration] =
    header.strings.length >= 2
      ? [header.strings[0]!, header.strings[1]!]
      : ["", header.strings[0] ?? ""];
  const differs = (shown: string | null | undefined, written: string) => {
    const text = unescapeWritten(written);
    return text !== null && (shown ?? "") !== text;
  };
  return differs(entry.payee, payee) || differs(entry.narration, narration);
}

/** A slice whose first line is a dated directive that is not a transaction (a pad). */
function sliceOpensAnotherKind(slice: string): boolean {
  const line = slice
    .split("\n")
    .map((text) => text.trim())
    .find((text) => text !== "" && !text.startsWith(";"));
  const match = line === undefined ? null : HEADER.exec(line);
  return match !== null && /^[a-z]+$/.test(match[2]!) && match[2] !== "txn";
}
