import { Buffer } from "buffer";

export function decodeLedgerFileContent(
  content: string,
  encoding?: string | null,
): string {
  if (encoding !== "base64") return content;
  return Buffer.from(content.replace(/\s/g, ""), "base64").toString("utf8");
}

export function encodeLedgerFileContent(content: string): string {
  return Buffer.from(content, "utf8").toString("base64");
}

/**
 * Whether decoding a file as UTF-8 and writing it back reproduces its bytes
 * (w21/042). A Latin-1 `é` decodes to U+FFFD, and saving any unrelated edit
 * wrote `EF BF BD` over it with no warning. A UTF-8 BOM round-trips.
 */
export function isLosslessLedgerFileContent(
  content: string,
  encoding?: string | null,
): boolean {
  if (encoding !== "base64") return true;
  const bytes = Buffer.from(content.replace(/\s/g, ""), "base64");
  return Buffer.from(bytes.toString("utf8"), "utf8").equals(bytes);
}

export type LineEnding = "\r\n" | "\n";

/**
 * The line ending most of a file's lines use. The editor joins its lines with
 * `\n`, so saving a CRLF ledger (Windows, or a Windows tool's export) rewrote
 * every line ending and turned a one-line edit into a whole-file diff
 * (w21/062). A mixed file keeps its majority; a tie stays `\n`.
 */
export function lineEndingOf(text: string): LineEnding {
  const crlf = text.match(/\r\n/g)?.length ?? 0;
  const all = text.match(/\n/g)?.length ?? 0;
  return crlf > all - crlf ? "\r\n" : "\n";
}

/** `content`'s line breaks written as `ending`. */
export function withLineEnding(content: string, ending: LineEnding): string {
  return content.replace(/\r?\n/g, ending);
}
