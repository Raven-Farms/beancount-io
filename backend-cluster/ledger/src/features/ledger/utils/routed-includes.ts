/**
 * `include` lines for files a write reaches outside the ledger's include
 * closure (w23/062). A `transaction_file "txns/{year}.bean"` rule routes the
 * first entry of a new year to a file per-year includes do not name yet;
 * without an include the entry commits and no report sees it.
 *
 * Each line goes after the entry point's last `include`, so a per-year list
 * stays together, or at its end when it has none.
 */
export function addIncludes(content: string, paths: readonly string[]): string {
  if (paths.length === 0) return content;
  const block = paths.map(
    (path) => `include "${path.replace(/[\\"]/g, "\\$&")}"`,
  );
  const lines = content.split("\n");
  const last = lines.findLastIndex((line) => /^\s*include\s/.test(line));
  if (last >= 0) {
    lines.splice(last + 1, 0, ...block);
    return lines.join("\n");
  }
  const body = content.replace(/\n+$/, "");
  return `${body}${body ? "\n" : ""}${block.join("\n")}\n`;
}
