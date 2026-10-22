import { toAsciiNumerals } from "../../common/ascii-numerals";
import { getFormatDate } from "../../common/format-util";
import type {
  AddEntryInput,
  BudgetInterval,
  LedgerEntryType,
} from "../../generated-graphql/types";

export type BudgetEntryInput = {
  account: string;
  /** Uppercase schema cadence, e.g. "MONTHLY". */
  interval: string;
  /**
   * Amount as typed. Kept a string all the way to the server so the ledger
   * records exactly what the user entered, and because a negative amount is
   * meaningful: it declares an income target rather than a spending cap. The
   * one change is the sign: an income target is stored negative and any other
   * budget positive (see `incomeRoot`).
   */
  number: string;
  currency: string;
  date: Date;
  /**
   * The ledger's income root (`name_income`). A budget on an account under it
   * is an income target and is stored negative whatever sign was typed, so the
   * user does not have to know the convention for its status to read right.
   * Any other account's budget is stored positive whatever sign was typed: a
   * negative amount reads as an income target, so an Expenses cap typed "-500"
   * showed always red and "0% used" (w21/302). Unknown (the ledger's roots not
   * loaded) leaves the text as typed.
   */
  incomeRoot?: string;
};

/**
 * Whether typed text is an amount the ledger can parse: an optional sign,
 * digits, and an optional decimal part with digits after the point. The text
 * is otherwise written verbatim, so `12..3`, `abc` or `1 000` used to commit
 * an unparsable `custom "budget"` line (w0/038). Grouping commas and exponents
 * are refused rather than rewritten: the user types the plain number.
 */
export function isBudgetAmount(text: string): boolean {
  // Digits from any keyboard count; they are written as ASCII (w21/392).
  return /^[+-]?\d+(\.\d+)?$/u.test(toAsciiNumerals(text).trim());
}

function isIncomeAccount(account: string, incomeRoot?: string): boolean {
  return (
    Boolean(incomeRoot) &&
    (account === incomeRoot || account.startsWith(`${incomeRoot}:`))
  );
}

/** A target typed as the positive amount someone hopes to earn, stored negative. */
function asIncomeTarget(amount: string): string {
  if (amount.startsWith("-")) return amount;
  const unsigned = amount.replace(/^\+/u, "");
  return Number(unsigned) === 0 ? unsigned : `-${unsigned}`;
}

/** A spending cap typed with a sign: stored as the positive amount. */
function asSpendingCap(amount: string): string {
  return amount.replace(/^[+-]/u, "");
}

/**
 * Build the single schema input that writes a Beancount `custom "budget"`
 * directive. There is no update mutation: revising a budget means adding a
 * newer-dated entry, which supersedes the previous one from its date.
 */
export function buildBudgetEntry({
  account,
  interval,
  number,
  currency,
  date,
  incomeRoot,
}: BudgetEntryInput): AddEntryInput {
  const trimmedAccount = account.trim();
  const amount = toAsciiNumerals(number).trim();
  return {
    type: "BUDGET" as LedgerEntryType,
    budget: {
      account: trimmedAccount,
      interval: interval.toUpperCase() as BudgetInterval,
      date: getFormatDate(date),
      amount: {
        number: !incomeRoot
          ? amount
          : isIncomeAccount(trimmedAccount, incomeRoot)
            ? asIncomeTarget(amount)
            : asSpendingCap(amount),
        currency: currency.trim().toUpperCase(),
      },
    },
  };
}
