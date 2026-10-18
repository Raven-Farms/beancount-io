import {
  negateDecimalNumber,
  parseDecimalNumber,
  sumDecimalNumbers,
} from "@/common/lib/beancount/decimal-number";

export type TransactionPostingDraft = {
  account: string;
  amount: string;
  currency: string;
};

/** An inferred balancing amount, as the plain decimal that is submitted. */
export type AutoBalanceEntry = { amount: string; currency: string };

export type AutoBalanceResult = {
  /** Inferred amount for a single empty eligible posting index. */
  balances: Map<number, AutoBalanceEntry>;
  /**
   * True when any currency group among eligible postings has more than one
   * empty amount, or a lone empty amount with no valid filled amounts.
   */
  incomplete: boolean;
};

export function isEligiblePosting(posting: TransactionPostingDraft): boolean {
  return posting.account.trim() !== "";
}

/**
 * Infer at most one missing amount per currency among postings that will be
 * written (non-empty account). Unused trailing/blank-account rows are ignored.
 * The residual is summed in decimal, so `0.1` and `0.2` balance to `-0.3`
 * rather than a double's `-0.30000000000000004`.
 */
export function computeAutoBalance(
  postings: TransactionPostingDraft[],
  primaryCurrency: string,
): AutoBalanceResult {
  const currencyGroups = new Map<
    string,
    { filled: string[]; emptyIndexes: number[] }
  >();

  postings.forEach((posting, index) => {
    if (!isEligiblePosting(posting)) return;

    const currency = posting.currency.trim() || primaryCurrency;
    let group = currencyGroups.get(currency);
    if (!group) {
      group = { filled: [], emptyIndexes: [] };
      currencyGroups.set(currency, group);
    }

    const parsed = parseDecimalNumber(posting.amount);
    if (parsed !== null) {
      group.filled.push(parsed);
    } else if (posting.amount.trim() === "") {
      group.emptyIndexes.push(index);
    }
  });

  const balances = new Map<number, AutoBalanceEntry>();
  let incomplete = false;

  currencyGroups.forEach((group, currency) => {
    if (group.emptyIndexes.length === 0) return;

    if (group.emptyIndexes.length === 1 && group.filled.length > 0) {
      balances.set(group.emptyIndexes[0], {
        amount: negateDecimalNumber(sumDecimalNumbers(group.filled)),
        currency,
      });
      return;
    }

    incomplete = true;
  });

  return { balances, incomplete };
}

export function applyAutoBalanceToPostings(
  postings: TransactionPostingDraft[],
  balances: Map<number, AutoBalanceEntry>,
): TransactionPostingDraft[] {
  return postings.map((posting, index) => {
    const autoBalance = balances.get(index);
    if (
      autoBalance &&
      isEligiblePosting(posting) &&
      posting.amount.trim() === ""
    ) {
      return {
        ...posting,
        amount: autoBalance.amount,
      };
    }
    return posting;
  });
}

/** Eligible postings after inference must all have valid decimal amounts. */
export function findUnresolvedEligibleAmount(
  postings: TransactionPostingDraft[],
): number | null {
  for (let index = 0; index < postings.length; index++) {
    const posting = postings[index];
    if (!isEligiblePosting(posting)) continue;
    if (parseDecimalNumber(posting.amount) === null) return index;
  }
  return null;
}

/** What a currency's postings fail to balance by, as `"1 USD"` reads. */
export type PostingResidual = { amount: string; currency: string };

/**
 * Currencies whose fully specified eligible postings do not sum to zero
 * within Beancount's default inferred tolerance, which the ledger would
 * refuse as UNBALANCED. Run after inference; unparseable amounts are left
 * to `findUnresolvedEligibleAmount`.
 */
export function findUnbalancedResiduals(
  postings: TransactionPostingDraft[],
  primaryCurrency: string,
): PostingResidual[] {
  const groups = new Map<string, string[]>();
  for (const posting of postings) {
    if (!isEligiblePosting(posting)) continue;
    const amount = parseDecimalNumber(posting.amount);
    if (amount === null) continue;
    const currency = posting.currency.trim() || primaryCurrency;
    groups.set(currency, [...(groups.get(currency) ?? []), amount]);
  }

  const residuals: PostingResidual[] = [];
  groups.forEach((amounts, currency) => {
    const residual = sumDecimalNumbers(amounts);
    if (exceedsInferredTolerance(residual, amounts)) {
      residuals.push({ amount: residual, currency });
    }
  });
  return residuals;
}

const decimalPlaces = (value: string) => value.split(".")[1]?.length ?? 0;

/**
 * Beancount infers half the last decimal place of each amount and keeps the
 * largest (`10.00` with `-9.999` tolerates 0.005); an integer amount infers
 * none, so all-integer postings must balance exactly.
 */
function exceedsInferredTolerance(
  residual: string,
  amounts: readonly string[],
): boolean {
  const places = amounts.map(decimalPlaces);
  const scale = Math.max(0, ...places) + 1;
  const [whole, fraction = ""] = residual.replace(/^-/, "").split(".");
  const magnitude = BigInt(whole + fraction.padEnd(scale, "0"));
  const fractional = places.filter((p) => p > 0);
  if (fractional.length === 0) return magnitude !== 0n;
  const tolerance = 5n * 10n ** BigInt(scale - Math.min(...fractional) - 1);
  return magnitude > tolerance;
}
