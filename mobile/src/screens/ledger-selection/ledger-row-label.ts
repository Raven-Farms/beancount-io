import { ledgerRowDescription } from "./ledger-row-description";

/**
 * What a Browse ledgers row says aloud. A label on a pressable replaces its
 * children, so "Open qa/my-book" alone hid the Private or Public line and the
 * description: on Starred and Yours a VoiceOver user could not tell private
 * ledgers from public ones (w21/243). Visibility comes straight after the
 * name, then the description, then "Current" for the open ledger.
 */
export function ledgerRowAccessibilityLabel({
  open,
  visibility,
  description,
  current,
}: {
  /** "Open {name}". */
  open: string;
  /** "Private" or "Public". */
  visibility: string;
  description: string | null | undefined;
  /** "Current", for the ledger that is open now; omitted otherwise. */
  current?: string;
}): string {
  return [open, visibility, ledgerRowDescription(description), current]
    .filter((part): part is string => Boolean(part))
    .join(", ");
}
