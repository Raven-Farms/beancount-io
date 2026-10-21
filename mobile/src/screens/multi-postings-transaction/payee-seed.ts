import type { Posting } from "./postings-utils";

/** A payee's usual accounts, from its two-posting history. */
export type PayeeHistory = {
  from: { autoFill: string | null };
  to: { autoFill: string | null };
};

type DraftPosting = Pick<Posting, "account" | "amountInput">;

const untouched = (
  current: readonly Posting[],
  initial: readonly DraftPosting[],
) =>
  current.length === 2 &&
  initial.length === 2 &&
  current.every(
    (posting, index) =>
      posting.account === initial[index]!.account &&
      posting.amountInput === initial[index]!.amountInput,
  );

/**
 * The postings to show once a known payee is picked: its usual source and
 * target accounts, so a repeat entry needs no account picks — what the keypad
 * flow did before multi-posting became the default (w21/023). Null leaves the
 * postings alone: the user already changed them, the form holds a split, or
 * the payee has no two-posting history on both sides. Amounts are never
 * touched.
 */
export function seedPostingsFromPayee(
  current: readonly Posting[],
  initial: readonly DraftPosting[],
  history: PayeeHistory,
): Posting[] | null {
  const from = history.from.autoFill;
  const to = history.to.autoFill;
  if (!from || !to || !untouched(current, initial)) return null;
  return [
    { ...current[0]!, account: from },
    { ...current[1]!, account: to },
  ];
}
