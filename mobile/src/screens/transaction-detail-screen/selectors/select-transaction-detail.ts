import type { RootNames } from "../../../common/account-root";
import type { JournalTransaction } from "../../transactions-screen/types";
import {
  isMixedPostingsAmount,
  selectTransactionAmount,
} from "../../transactions-screen/utils/transaction-display-utils";
import { formatEntryRowAmount } from "../../transactions-screen/entry-row/format-entry-row-amount";

// Beancount/Fava reserve these flags for entries synthesized by reports or
// plugins. They are not standalone source directives, so asking the source
// context API to edit or delete one either fails or resolves to the directive
// that generated it (for example, a `pad` directive instead of its `P`
// transaction).
const GENERATED_TRANSACTION_FLAGS = new Set([
  "P",
  "S",
  "T",
  "C",
  "U",
  "R",
  "M",
]);

export function hasEditableSource(txn: JournalTransaction): boolean {
  return !GENERATED_TRANSACTION_FLAGS.has(txn.flag);
}

/** Headline amount for the detail screen, signed exactly as the list row is:
 * `+` for money in, `-` for money out, unsigned with no direction. */
export type HeroAmount = {
  text: string;
  isPositive: boolean | null;
};

/**
 * The headline amount, from the same selector `EntryRow` uses for list
 * rows, so the hero number can never disagree with the row the user tapped.
 *
 * @param mixedLabel - Localized neutral summary shown, unsigned and uncolored,
 *   for a trade whose money side spans several accounts (see
 *   `selectTransactionAmount`); its exact postings are listed below the hero.
 */
export function selectHeroAmount(
  txn: JournalTransaction,
  mixedLabel: string,
  operatingCurrency?: string,
  roots?: RootNames,
): HeroAmount {
  const amount = selectTransactionAmount(txn, operatingCurrency, roots);
  if (!amount) {
    return { text: "", isPositive: null };
  }
  if (isMixedPostingsAmount(amount)) {
    return { text: mixedLabel, isPositive: null };
  }

  const { text, value } = amount;
  return {
    text: formatEntryRowAmount(text, value),
    isPositive: value > 0 ? true : value < 0 ? false : null,
  };
}

/** One posting shaped for display: signed amount string + sign for coloring. */
export type PostingDisplayRow = {
  account: string;
  amount: string;
  sign: -1 | 0 | 1;
  /** Per-unit lot cost, unsigned, when the posting holds one (`{1.50 USD}`). */
  cost?: string;
  /** Per-unit price, unsigned, when the posting carries one (`@ 2.00 USD`). */
  price?: string;
};

/**
 * Format a posting units number from its recorded decimal string so commodity
 * quantities keep their source scale (e.g. 1.843 RGAGX). USD still pads to
 * two fraction digits when the source is shorter. Avoids parseFloat →
 * maximumFractionDigits: 2 which rounded share quantities away.
 */
function formatPostingUnits(
  number: string,
  currency: string,
): {
  amount: string;
  sign: -1 | 0 | 1;
} {
  const trimmed = number.trim();
  if (!/^[+-]?\d+(\.\d+)?$/.test(trimmed)) {
    return { amount: `${number} ${currency}`, sign: 0 };
  }

  const negative = trimmed.startsWith("-");
  const unsigned = trimmed.replace(/^[+-]/, "");
  const isZero = /^0+(\.0+)?$/.test(unsigned);
  const [intPart, fracPart = ""] = unsigned.split(".");
  const displayFrac =
    currency === "USD" && fracPart.length < 2
      ? fracPart.padEnd(2, "0")
      : fracPart;
  const groupedInt = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const body =
    displayFrac.length > 0 ? `${groupedInt}.${displayFrac}` : groupedInt;
  const magnitude = currency === "USD" ? `$${body}` : `${body} ${currency}`;

  if (isZero) {
    return { amount: magnitude, sign: 0 };
  }
  if (negative) {
    return { amount: `-${magnitude}`, sign: -1 };
  }
  return { amount: `+${magnitude}`, sign: 1 };
}

/** More fractional digits than anyone writes: a total divided per unit. */
const DERIVED_SCALE = 8;
/** Significant decimals a derived per-unit figure is shown to. */
const DERIVED_DIGITS = 4;

/**
 * A per-unit figure the ledger derived from a total (`@@ 10.00 USD` on three
 * units, `{{…}}`), rounded half-up to four significant decimals. Divided at
 * full precision it read "@ $3.3333333333333333333333333333" and squeezed
 * the account name to an ellipsis (w21/160). Null for a figure as written.
 */
function roundDerivedPerUnit(number: string): string | null {
  const negative = number.startsWith("-");
  const [whole, frac = ""] = number.replace(/^[+-]/, "").split(".");
  if (frac.length <= DERIVED_SCALE) return null;
  const leadingZeros = /^0*/.exec(whole === "0" ? frac : "")![0].length;
  const scale = Math.min(frac.length, leadingZeros + DERIVED_DIGITS);
  const digits = BigInt(`${whole}${frac.slice(0, scale)}`);
  const rounded = Number(frac[scale]) >= 5 ? digits + 1n : digits;
  const text = rounded.toString().padStart(scale + 1, "0");
  const roundedFrac = text.slice(-scale).replace(/0+$/, "");
  const roundedWhole = text.slice(0, -scale);
  return `${negative ? "-" : ""}${roundedWhole}${roundedFrac ? `.${roundedFrac}` : ""}`;
}

/** A per-unit cost or price at its recorded scale, without a sign. */
const formatPerUnit = (amount: {
  number: string;
  currency: string;
}): string => {
  const derived = roundDerivedPerUnit(amount.number.trim());
  const shown = formatPostingUnits(
    derived ?? amount.number,
    amount.currency,
  ).amount.replace(/^[+-]/, "");
  return derived === null ? shown : `≈${shown}`;
};

export function selectPostingRows(
  txn: JournalTransaction,
): PostingDisplayRow[] {
  return (txn.postings ?? []).map((p) => {
    const { amount, sign } = formatPostingUnits(
      p.units.number,
      p.units.currency,
    );
    return {
      account: p.account,
      amount,
      sign,
      // A trade's cost basis and sale price explain its gain; the row used
      // to show only the units (w21/059).
      ...(p.cost?.number && p.cost.currency
        ? { cost: formatPerUnit(p.cost) }
        : {}),
      ...(p.price?.number && p.price.currency
        ? { price: formatPerUnit(p.price) }
        : {}),
    };
  });
}

/**
 * The line under a posting's units naming its cost and price, or null for an
 * ordinary posting. A price alone reads as the ledger writes it, `@ 1.10 USD`.
 */
export function postingBasisText(
  row: Pick<PostingDisplayRow, "cost" | "price">,
  t: (
    key: "postingCost" | "postingPrice",
    params: { amount: string },
  ) => string,
): string | null {
  if (row.cost && row.price) {
    return `${t("postingCost", { amount: row.cost })} · ${t("postingPrice", { amount: row.price })}`;
  }
  if (row.cost) return t("postingCost", { amount: row.cost });
  if (row.price) return `@ ${row.price}`;
  return null;
}

export function selectTransactionTitle(txn: JournalTransaction): string {
  return txn.payee || txn.narration || "";
}

/** An overflow-menu action on the transaction detail screen. */
export type TransactionMenuAction =
  "shareLink" | "copyLink" | "deleteTransaction";

/**
 * Which overflow-menu actions a transaction offers, in display order.
 *
 * A generated entry (see `hasEditableSource`) has no source directive, so an
 * entry permalink opens "No entry context data available" rather than the
 * transaction — offering Share/Copy there hands the user a broken link. Write
 * actions keep their own gate (`shouldShowTransactionWriteActions`), which
 * needs a loaded `sha256sum` and so is already false for a generated entry.
 *
 * @returns The actions to show; an empty list means render no menu button at
 *   all, since an ellipsis that opens nothing is worse than no ellipsis.
 */
export function selectTransactionMenuActions({
  isGenerated,
  showWriteActions,
}: {
  isGenerated: boolean;
  showWriteActions: boolean;
}): TransactionMenuAction[] {
  const actions: TransactionMenuAction[] = [];
  if (!isGenerated) {
    actions.push("shareLink", "copyLink");
  }
  if (showWriteActions) {
    actions.push("deleteTransaction");
  }
  return actions;
}
