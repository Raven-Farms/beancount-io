import type { ParsedTransaction } from "../../types";

const XML_ENTITIES: Record<string, string> = {
  amp: "&",
  lt: "<",
  gt: ">",
  quot: '"',
  apos: "'",
};

const COMPARISON_FORMAT_BY_MEDIA_TYPE: Record<string, string> = {
  "application/qif": "qif",
  "application/x-qif": "qif",
  "text/qif": "qif",
  "application/x-ofx": "xml",
  "application/vnd.intu.qfx": "xml",
  "application/xml": "xml",
  "text/xml": "xml",
};

function comparisonText(
  sourceText: string,
  format: string,
  mediaType?: string,
): string {
  const mime = mediaType?.split(";")[0].trim().toLowerCase();
  const normalizedFormat =
    !mime || mime === "text/plain" || mime === "application/octet-stream"
      ? format.trim().toLowerCase()
      : (COMPARISON_FORMAT_BY_MEDIA_TYPE[mime] ?? "");
  if (normalizedFormat === "qif") {
    // QIF memo and split-memo markers attach directly to their printed text.
    return sourceText.replace(/^[ME]/gm, "");
  }
  if (!["ofx", "qfx", "xml"].includes(normalizedFormat)) return sourceText;
  return sourceText.replace(
    /&(amp|lt|gt|quot|apos|#(?:[xX][\dA-Fa-f]+|\d+));/g,
    (reference, entity: string) => {
      if (entity[0] !== "#") return XML_ENTITIES[entity];
      const hexadecimal = entity[1].toLowerCase() === "x";
      const codePoint = Number.parseInt(
        entity.slice(hexadecimal ? 2 : 1),
        hexadecimal ? 16 : 10,
      );
      const validXmlCharacter =
        codePoint === 0x9 ||
        codePoint === 0xa ||
        codePoint === 0xd ||
        (codePoint >= 0x20 && codePoint <= 0xd7ff) ||
        (codePoint >= 0xe000 && codePoint <= 0xfffd) ||
        (codePoint >= 0x10000 && codePoint <= 0x10ffff);
      return validXmlCharacter ? String.fromCodePoint(codePoint) : reference;
    },
  );
}

function normalizeTokens(text: string): string {
  return (
    text
      .normalize("NFKC")
      .toLowerCase()
      .match(/[\p{L}\p{N}][\p{L}\p{M}\p{N}]*/gu)
      ?.join(" ") ?? ""
  );
}

/** File-level grounding: words must occur together, in order, at token boundaries. */
export function groundTransactionDescriptions(
  transactions: ParsedTransaction[],
  sourceText: string,
  format: string,
  mediaType?: string,
): { transactions: ParsedTransaction[]; removedDescriptionCount: number } {
  const source = ` ${normalizeTokens(comparisonText(sourceText, format, mediaType))} `;
  let removedDescriptionCount = 0;
  const grounded = transactions.map((transaction) => {
    const description = transaction.description.trim();
    const normalized = normalizeTokens(description);
    if (description && (!normalized || !source.includes(` ${normalized} `))) {
      removedDescriptionCount++;
      return { ...transaction, description: "" };
    }
    return { ...transaction, description };
  });
  return { transactions: grounded, removedDescriptionCount };
}
