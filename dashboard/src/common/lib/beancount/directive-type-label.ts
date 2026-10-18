/**
 * Translation keys for Beancount directive type names, as the ledger reports
 * them (`"Balance"`, `"Open"`, …). Shared so every surface that names a
 * directive type uses the Journal's wording.
 */
const DIRECTIVE_TYPE_KEYS: Readonly<Record<string, string>> = {
  Open: "journal.open",
  Close: "journal.close",
  Transaction: "journal.transaction",
  Balance: "journal.balance",
  Note: "journal.note",
  Document: "journal.document",
  Pad: "journal.pad",
  Price: "journal.price",
  Custom: "journal.custom",
  Commodity: "journal.commodity",
  Event: "journal.event",
  Query: "journal.query",
};

/** The localized name of a directive type, or the type itself if unknown. */
export function directiveTypeLabel(
  type: string,
  t: (key: string) => string,
): string {
  const key = DIRECTIVE_TYPE_KEYS[type];
  return key ? t(key) : type;
}
