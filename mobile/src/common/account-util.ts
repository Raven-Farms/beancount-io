/** Separator between beancount account segments. */
export const SEGMENT_SEPARATOR = ":";

/**
 * Split an account into its parent path (separator included) and leaf segment,
 * so a row can dim the path and emphasize the part that identifies it.
 */
export function splitAccountLeaf(account: string): {
  parent: string;
  leaf: string;
} {
  const lastSeparator = account.lastIndexOf(SEGMENT_SEPARATOR);
  if (lastSeparator === -1) {
    return { parent: "", leaf: account };
  }
  return {
    parent: account.slice(0, lastSeparator + 1),
    leaf: account.slice(lastSeparator + 1),
  };
}

/** Leaf segment of a colon-delimited beancount account
 * (e.g. "Assets:Bank:Checking" → "Checking"). */
export function leafName(account: string): string {
  // Falls back to the whole account for a trailing separator, where the leaf
  // is empty ("Assets:" → "Assets:").
  return splitAccountLeaf(account).leaf || account;
}

/** Everything below the root (e.g. "Expenses:Food:Groceries" → "Food:Groceries").
 * Keeps the branch a row sits on, which `leafName` drops. */
export function dropRoot(account: string): string {
  const parts = account.split(SEGMENT_SEPARATOR);
  return parts.length > 1 ? parts.slice(1).join(SEGMENT_SEPARATOR) : account;
}

/**
 * The account with a zero-width space after each separator, so a line breaks
 * between its components. At the largest text sizes an account is one unbroken
 * token and wrapped mid-word ("Assets:Bank:Checkin" / "g"); this wraps it as
 * "Assets:Bank:" / "Checking" (w21/627). For display only: the account itself,
 * and what VoiceOver reads, are unchanged.
 */
export function breakableAccount(account: string): string {
  return account.split(SEGMENT_SEPARATOR).join(`${SEGMENT_SEPARATOR}​`);
}
