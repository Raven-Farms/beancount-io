import {
  type JournalDirectiveType,
  isJournalBalance,
  isJournalCustom,
  isJournalDocument,
  isJournalTransaction,
} from "@/common/types/journal";
import { formatDateISO } from "@/common/lib/format/format-date-iso";
import { formatAmountWithCurrency } from "./journal-description/utils";

/** Bounded identity from the row's visible entry fields, never source metadata. */
export function journalEntryLabel(directive: JournalDirectiveType): string {
  const parts = [formatDateISO(directive.date) ?? ""];
  if (isJournalTransaction(directive)) {
    parts.push(directive.payee ?? "", directive.narration ?? "");
  } else {
    parts.push(directive.directive_type);
    if (isJournalBalance(directive)) {
      // A Balance carries `amount` too, so it must not reach the Price branch.
      parts.push(directive.account);
      if (directive.amount) {
        parts.push(formatAmountWithCurrency(directive.amount));
      }
      if (directive.diff_amount) {
        parts.push(formatAmountWithCurrency(directive.diff_amount));
      }
    } else if (isJournalDocument(directive)) {
      parts.push(directive.account, directive.filename.split("/").pop() ?? "");
    } else if (isJournalCustom(directive)) {
      parts.push(directive.type);
      for (const value of directive.values) {
        if (["string", "number", "boolean"].includes(typeof value)) {
          parts.push(String(value));
        } else if (
          value &&
          typeof value === "object" &&
          "number" in value &&
          typeof value.number === "string" &&
          "currency" in value &&
          typeof value.currency === "string"
        ) {
          parts.push(
            formatAmountWithCurrency({
              number: value.number,
              currency: value.currency,
            }),
          );
        }
      }
    } else if ("comment" in directive) {
      parts.push(directive.comment);
    } else if ("description" in directive) {
      parts.push(directive.type, directive.description);
    } else if ("amount" in directive) {
      parts.push(
        `${formatAmountWithCurrency(directive.amount)}/${directive.currency}`,
      );
    } else if ("currency" in directive) {
      parts.push(directive.currency);
    } else if ("account" in directive) {
      parts.push(directive.account);
      if ("source_account" in directive) parts.push(directive.source_account);
    }
  }

  const label = parts.join(" ").replace(/\s+/g, " ").trim();
  const characters = Array.from(label);
  return characters.length > 160
    ? `${characters.slice(0, 159).join("").trimEnd()}…`
    : label;
}
