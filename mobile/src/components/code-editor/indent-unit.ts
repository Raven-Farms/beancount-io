/**
 * What the editor indents with, and the text the accessory bar's ⇥ stands for.
 * Import-free so the unit runner can load it (w21/339).
 */

/**
 * The accessory bar's ⇥ inserts "one unit of this document's indentation", not
 * a fixed two spaces: a Makefile recipe needs a tab, and `make` fails with
 * "missing separator" on spaces. The bar sends this token and the editor swaps
 * in the unit.
 */
export const INSERT_INDENT = "\u0000indent";

/** How many leading lines are looked at; a large file is not scanned whole. */
const SCAN_LINES = 500;

/**
 * A tab when the document's indented lines mostly start with one, else two
 * spaces. A tab-indented Makefile or Python block followed by a line of
 * spaces is a syntax error ("missing separator", `IndentationError`).
 */
export function detectIndentUnit(text: string): string {
  let tabs = 0;
  let spaces = 0;
  let scanned = 0;
  for (const line of text.split("\n", SCAN_LINES)) {
    scanned += 1;
    if (line.startsWith("\t")) tabs += 1;
    else if (line.startsWith(" ") && line.trim() !== "") spaces += 1;
    if (scanned >= SCAN_LINES) break;
  }
  return tabs > spaces ? "\t" : "  ";
}

/**
 * A pair shortcut such as `""` or `()` — two characters with the cursor
 * between them — wraps a non-empty selection instead of replacing it. Returns
 * the text to put in place of the selection and where the new selection runs,
 * relative to the start, or null when the selection is empty or the insert is
 * not a pair.
 */
export function wrapSelection(
  insert: string,
  cursorOffset: number | undefined,
  selected: string,
): { text: string; selectFrom: number; selectTo: number } | null {
  if (selected === "" || cursorOffset !== 1 || insert.length !== 2) return null;
  return {
    text: `${insert[0]}${selected}${insert[1]}`,
    selectFrom: 1,
    selectTo: 1 + selected.length,
  };
}
