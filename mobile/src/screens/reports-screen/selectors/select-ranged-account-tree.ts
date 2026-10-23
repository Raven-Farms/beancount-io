import { isolateLtr } from "../../../common/bidi";
import {
  CATEGORY_SIGN,
  selectAccountTreeFromRoot,
} from "../../../components/account-list/select-account-list";
import type {
  AccountNode,
  CategoryKey,
} from "../../../components/account-list/select-account-list";
import { resolveCurrencyBalance } from "../../../common/balance-util";
import {
  formatHolding,
  notInTotalOf,
  type Holding,
  type Translate,
} from "../../../common/balance-display";
import {
  currentYearMonth,
  flowAnchorMonth,
  rangeStartMonth,
  type TimeRange,
} from "../../../common/series-util";

/** A monthly income/expense point carrying per-account balances. */
type MonthlyAccountPoint = {
  date: string;
  // Backend returns `{ account: { currency: amount } }` (see
  // ledger-data-resolver.query.ts); the schema types it as opaque JSONObject,
  // so we cast at the boundary below.
  accountBalances: unknown;
};

/**
 * An amount the card's total cannot include: a currency other than the one the
 * report is in, summed over the window under the top-level account it belongs
 * to (`Travel` for `Expenses:Travel:Hotel`), with the card's display sign.
 */
export type NotInTotalAmount = { account: string; holding: Holding };

/** The selector's result: the tree, its total, and what the total leaves out. */
export type RangedAccountTree = {
  tree: AccountNode[];
  total: number;
  notInTotal: NotInTotalAmount[];
};

const EMPTY: RangedAccountTree = { tree: [], total: 0, notInTotal: [] };

/** Node in the SerializableTreeNode shape `selectAccountTreeFromRoot` reads. */
type TreeNode = {
  account: string;
  balance?: Record<string, number>;
  balanceChildren: Record<string, number>;
  children: TreeNode[];
};

type Trie = { account: string; children: Map<string, Trie> };

function insertAccount(root: Trie, account: string): void {
  const parts = account.split(":");
  let node = root;
  let prefix = "";
  for (const part of parts) {
    prefix = prefix ? `${prefix}:${part}` : part;
    let child = node.children.get(prefix);
    if (!child) {
      child = { account: prefix, children: new Map() };
      node.children.set(prefix, child);
    }
    node = child;
  }
}

/**
 * Rolled-up signed sum of a node's OWN balance plus every descendant's.
 *
 * The backend's `accountBalances` reports each account's own, non-overlapping
 * balance — NOT a rolled-up parent total — so an account can appear with its own
 * postings AND alongside its sub-accounts. `Expenses:Taxes:…:Federal` (its own USD
 * withholding) sits next to `…:Federal:PreTax401k` (a 401k leg booked in a
 * commodity). Summing only trie *leaves* dropped the own balance of every account
 * that also has sub-accounts — e.g. Federal's USD — which is what made the Taxes
 * total under-report against the web dashboard. So every node contributes its own
 * `sums` entry (0 when it has none, e.g. a pure aggregating level the backend
 * never reported); there is no double-counting because parents carry only their
 * own direct postings.
 */
function rollup(trie: Trie, sums: Map<string, number>): number {
  let total = sums.get(trie.account) ?? 0;
  for (const child of trie.children.values()) {
    total += rollup(child, sums);
  }
  return withoutResidue(total);
}

/**
 * A sum of decimal amounts without its float residue: 10.10 + 20.20 − 30.30
 * is -3.55e-15 as floats, which kept a category that nets to zero as a
 * "−$0.00 · 0%" row and fed the Sankey a phantom node (w21/055). Ten decimals
 * is beyond any recorded scale; `|| 0` also turns -0 into 0.
 */
const withoutResidue = (value: number): number =>
  Number(value.toFixed(10)) || 0;

function toTreeNode(
  trie: Trie,
  currency: string,
  sums: Map<string, number>,
): TreeNode {
  return {
    account: trie.account,
    // Its own sum, kept so its postings get a row beside its sub-accounts
    // and the breakdown adds up (w21/174).
    balance: { [currency]: sums.get(trie.account) ?? 0 },
    balanceChildren: { [currency]: rollup(trie, sums) },
    children: Array.from(trie.children.values()).map((child) =>
      toTreeNode(child, currency, sums),
    ),
  };
}

/**
 * Build a range-scoped Income/Expense account breakdown from the income
 * statement's monthly per-account series (`incomeData` / `expensesData`).
 *
 * The hierarchy snapshots (`*HierarchyData`) are full-period, so to honor the
 * report's time-range pills we instead sum each account's monthly balance
 * across the selected window. The window is anchored to the latest data point's
 * month — the same convention the report charts use (`rangeStartMonth`) — so a
 * stale ledger still shows history instead of an empty list. The summed
 * per-account totals are rebuilt into the same expandable tree the Accounts tab
 * renders, via `selectAccountTreeFromRoot`. `category` picks the display sign
 * (income is stored as a credit, so it's negated to read positive); `total` is
 * the signed sum of the displayed top-level accounts, so the card headline always
 * matches its rows.
 */
export function selectRangedAccountTree(
  currency: string,
  points:
    readonly (MonthlyAccountPoint | null | undefined)[] | null | undefined,
  range: TimeRange,
  category: CategoryKey,
  currentMonth: string = currentYearMonth(),
): RangedAccountTree {
  if (!currency || !points || points.length === 0) {
    return EMPTY;
  }

  // Window: anchored to the latest point's month (matches filterSeriesByRange).
  const dated = points.filter((p): p is MonthlyAccountPoint => !!p?.date);
  if (dated.length === 0) {
    return EMPTY;
  }
  dated.sort((a, b) => a.date.localeCompare(b.date));
  // Never past the current month, so a pre-entered rent cheque does not move
  // the window onto next month (w21/166). "ALL" keeps everything.
  const anchor = flowAnchorMonth(
    dated[dated.length - 1].date.slice(0, 7),
    currentMonth,
  );
  const cutoff = rangeStartMonth(range, anchor);
  const ranged = cutoff
    ? dated.filter((p) => {
        const month = p.date.slice(0, 7);
        return month >= cutoff && month <= anchor;
      })
    : dated;

  // Sum each account's resolved balance across the window, and set aside what
  // that reading cannot include — another currency used to vanish from the
  // card with no hint, where Home and Accounts say "not in total" (w21/038).
  const sums = new Map<string, number>();
  const omitted = new Map<string, NotInTotalAmount>();
  const sign = CATEGORY_SIGN[category];
  for (const point of ranged) {
    const accountBalances = (point.accountBalances ?? {}) as Record<
      string,
      Record<string, number | string> | null | undefined
    >;
    for (const [account, balances] of Object.entries(accountBalances)) {
      if (!account) {
        continue;
      }
      const value = resolveCurrencyBalance(balances ?? {}, currency);
      sums.set(account, withoutResidue((sums.get(account) ?? 0) + value));
      const topLevel = account.split(":")[1] ?? account;
      for (const holding of notInTotalOf(balances, currency)) {
        const key = `${topLevel}\0${holding.currency}`;
        const prior = omitted.get(key)?.holding;
        const scale = Math.max(prior?.scale ?? 0, holding.scale);
        omitted.set(key, {
          account: topLevel,
          holding: {
            currency: holding.currency,
            scale,
            // Rounded to the recorded scale so summing decimals as floats
            // cannot print 50.000000000000004.
            number: Number(
              ((prior?.number ?? 0) + sign * holding.number).toFixed(scale),
            ),
          },
        });
      }
    }
  }
  const notInTotal = [...omitted.values()].filter(
    ({ holding }) => holding.number !== 0,
  );
  if (sums.size === 0) {
    return EMPTY;
  }

  // Build a trie from the account paths, roll up leaf sums, and convert to the
  // SerializableTreeNode shape. Skip the category level (e.g. "Income") so
  // dropRoot names the top-level accounts the same way the Accounts tab
  // does — the synthetic root's children are the depth-1 accounts.
  const root: Trie = { account: "", children: new Map() };
  sums.forEach((_v, account) => insertAccount(root, account));

  const topLevel: TreeNode[] = [];
  for (const category of root.children.values()) {
    if (category.children.size > 0) {
      for (const topAccount of category.children.values()) {
        topLevel.push(toTreeNode(topAccount, currency, sums));
      }
    } else {
      // Defensive: an account with no category prefix — surface it as-is.
      topLevel.push(toTreeNode(category, currency, sums));
    }
  }
  if (topLevel.length === 0) {
    return { ...EMPTY, notInTotal };
  }

  const fakeRoot: TreeNode = {
    account: "root",
    balanceChildren: {},
    children: topLevel,
  };
  const tree = selectAccountTreeFromRoot(
    currency,
    fakeRoot,
    CATEGORY_SIGN[category],
  );
  const total = withoutResidue(tree.reduce((sum, node) => sum + node.value, 0));
  return { tree, total, notInTotal };
}

/**
 * The card's "Not in total: 50 EUR (Travel)" line, or nothing when the total
 * leaves nothing out.
 */
export function notInTotalNote(
  amounts: readonly NotInTotalAmount[],
  t: Translate,
): string | null {
  return amounts.length === 0
    ? null
    : t("notInTotal", {
        amounts: amounts
          // Each "50 EUR (Travel)" isolated (w21/249).
          .map(({ account, holding }) =>
            isolateLtr(`${formatHolding(holding)} (${account})`),
          )
          .join(", "),
      });
}

/**
 * What the charts say for a range with no flow in the operating currency: that
 * there is none, and, when the range does have flow in another currency, what
 * the totals leave out. "No cash flow" beside a card listing 420 EUR as not in
 * the total asserted something false (w21/515).
 */
export function emptyFlowLabel(
  noFlow: string,
  notInTotal: readonly NotInTotalAmount[],
  t: Translate,
): string {
  const note = notInTotalNote(notInTotal, t);
  return note ? `${noFlow} ${note}` : noFlow;
}
