import fs from "fs";
import path from "path";
import { getAccountRoot } from "../common/account-root";
import { matchCategory, pickPrimaryAccount } from "../common/tx-category";
import {
  ACCOUNT_ROOT_PREFIXES,
  composeAccountName,
  ledgerRootName,
  peelTypedRoot,
  splitPrefillAccountName,
  validateAccountName,
} from "../screens/open-account-screen/account-name";
import { selectTransactionAmount } from "../screens/transactions-screen/utils/transaction-display-utils";
import type { JournalTransaction } from "../screens/transactions-screen/types";
import { buildPayeeSeriesBql } from "../screens/merchants-screen/selectors/payee-series";
import { buildMerchantCurrencyTotalsBql } from "../screens/merchant-detail-screen/selectors/merchant-stats";
import {
  categorizeAccount,
  isExcludedAccount,
  sankeyRoleForId,
  transformToSankeyData,
} from "../screens/reports-screen/selectors/sankey-data";
import type { AccountNode } from "../components/account-list/select-account-list";

/**
 * w21/073: a ledger may rename its roots (`option "name_assets" "Activos"`).
 * Open Account, Reports' Recent transactions, the Merchants statements and the
 * transaction rows only knew the English names.
 */
const roots = {
  assets: "Activos",
  liabilities: "Pasivos",
  equity: "Patrimonio",
  income: "Ingresos",
  expenses: "Gastos",
};
const allRootNames = ACCOUNT_ROOT_PREFIXES.map((root) =>
  ledgerRootName(root, roots),
);

describe("Open Account on a renamed-roots ledger", () => {
  it("offers and writes the ledger's own root", () => {
    expect(allRootNames).toEqual([
      "Activos",
      "Pasivos",
      "Patrimonio",
      "Ingresos",
      "Gastos",
    ]);
    const account = composeAccountName(
      ledgerRootName("Assets", roots),
      "Banco",
    );
    expect(account).toBe("Activos:Banco");
    expect(validateAccountName(account, allRootNames)).toEqual({ ok: true });
    expect(validateAccountName("Assets:Banco", allRootNames)).toEqual({
      ok: false,
      reason: "invalidRoot",
    });
  });

  it("moves a typed or prefilled renamed root into the selector", () => {
    expect(peelTypedRoot("Activos:Banco", "Expenses", roots)).toEqual({
      rootPrefix: "Assets",
      subPath: "Banco",
    });
    expect(splitPrefillAccountName("gastos:Comida", "Assets", roots)).toEqual({
      rootPrefix: "Expenses",
      subPath: "Comida",
    });
  });

  it("leaves English ledgers as they were", () => {
    expect(ACCOUNT_ROOT_PREFIXES.map((root) => ledgerRootName(root))).toEqual([
      ...ACCOUNT_ROOT_PREFIXES,
    ]);
    expect(peelTypedRoot("Assets:Bank", "Expenses")).toEqual({
      rootPrefix: "Assets",
      subPath: "Bank",
    });
  });
});

describe("transaction rows on a renamed-roots ledger", () => {
  const purchase = {
    postings: [
      {
        account: "Gastos:Restaurantes",
        units: { number: "12.50", currency: "EUR" },
      },
      {
        account: "Activos:Banco",
        units: { number: "-12.50", currency: "EUR" },
      },
    ],
  } as unknown as JournalTransaction;

  it("resolves each root by the ledger's name", () => {
    expect(getAccountRoot("Gastos:Restaurantes", roots)).toBe("expenses");
    expect(getAccountRoot("Activos:Banco", roots)).toBe("assets");
    expect(getAccountRoot("Expenses:Food")).toBe("expenses");
  });

  it("signs a purchase and gives it its category, not a transfer glyph", () => {
    const amount = selectTransactionAmount(purchase, "EUR", roots);
    expect(amount).toEqual({
      text: "12.50 EUR",
      value: -12.5,
      currency: "EUR",
    });
    expect(
      pickPrimaryAccount(
        purchase.postings.map((p) => ({
          account: p.account,
          amount: Number(p.units.number),
        })),
        roots,
      ),
    ).toBe("Gastos:Restaurantes");
    expect(matchCategory("Gastos:Restaurant", roots)).toBe("restaurant");
    expect(matchCategory("Gastos:Restaurant")).toBe(null);
  });

  it("is what the rows, the hero and the icon are given", () => {
    const read = (...parts: string[]) =>
      fs.readFileSync(path.join(__dirname, "..", ...parts), "utf8");
    expect(
      read("screens", "transactions-screen", "entry-row", "index.tsx").includes(
        "const roots = useLedgerRootNames();",
      ),
    ).toBe(true);
    expect(
      read(
        "screens",
        "transaction-detail-screen",
        "transaction-detail-screen.tsx",
      ).includes("const roots = useLedgerRootNames();"),
    ).toBe(true);
    expect(
      read("components", "account-type-icon", "index.tsx").includes(
        "resolveGlyph(postings, roots, operatingCurrency)",
      ),
    ).toBe(true);
  });
});

describe("Reports and Merchants on a renamed-roots ledger", () => {
  it("query the ledger's Expenses and Income roots", () => {
    const named = { expenses: "Gastos", income: "Ingresos" };
    expect(
      buildPayeeSeriesBql("2023-10-21", named).includes(
        "(account ~ '^Gastos' OR account ~ '^Ingresos')",
      ),
    ).toBe(true);
    expect(
      buildMerchantCurrencyTotalsBql("Café", named).includes(
        "(account ~ '^Gastos' OR account ~ '^Ingresos')",
      ),
    ).toBe(true);
    // English ledgers send the statement they always did.
    expect(
      buildPayeeSeriesBql("2023-10-21").includes(
        "(account ~ '^Expenses' OR account ~ '^Income')",
      ),
    ).toBe(true);
  });

  it("lists Recent transactions under the ledger's roots", () => {
    const source = fs.readFileSync(
      path.join(
        __dirname,
        "..",
        "screens",
        "reports-screen",
        "reports-screen.tsx",
      ),
      "utf8",
    );
    expect(source.includes("accountPrefix={moneyRoots}")).toBe(true);
    expect(source.includes('accountPrefix={["Income", "Expenses"]}')).toBe(
      false,
    );
  });
});

// w21/235: the Cash flow card classified accounts by the English root names,
// so a ledger that renames its roots drew "No cash flow in this range" under a
// chart full of income and spending.
describe("Reports' Cash flow on a renamed-roots ledger", () => {
  const node = (account: string, value: number): AccountNode => ({
    account,
    name: account.split(":").pop() as string,
    value,
    children: [],
  });
  const labels = {
    otherLabel: "Other",
    cashFlowLabel: "Cash flow",
    savingsLabel: "Savings",
    refundsLabel: "Refunds",
    clawbacksLabel: "Clawbacks",
  };
  const flows = (
    income: AccountNode[],
    expenses: AccountNode[],
    ledgerRoots?: typeof roots | Partial<typeof roots>,
  ) =>
    transformToSankeyData({
      income,
      expenses,
      ...labels,
      ...(ledgerRoots ? { roots: ledgerRoots } : {}),
    });

  it("draws the same flow as the English ledger", () => {
    const english = flows(
      [node("Income:Salario", 3000)],
      [node("Expenses:Vivienda", 1200), node("Expenses:Comida", 800)],
    );
    const renamed = flows(
      [node("Ingresos:Salario", 3000)],
      [node("Gastos:Vivienda", 1200), node("Gastos:Comida", 800)],
      roots,
    );
    expect(renamed.links.length > 0).toBe(true);
    expect(renamed.nodes.map((n) => n.label)).toEqual(
      english.nodes.map((n) => n.label),
    );
    expect(renamed.links.map((l) => l.value)).toEqual(
      english.links.map((l) => l.value),
    );
    expect(renamed.nodes.map((n) => n.role)).toEqual(
      english.nodes.map((n) => n.role),
    );
    expect(renamed.nodes.some((n) => n.label === "Savings")).toBe(true);
  });

  it("is empty without the roots, which is the bug", () => {
    const hidden = flows(
      [node("Ingresos:Salario", 3000)],
      [node("Gastos:Vivienda", 1200)],
    );
    expect(hidden.links).toEqual([]);
  });

  it("does not claim all income was saved when only expenses are renamed", () => {
    const partial = { expenses: "Gastos" };
    const data = flows(
      [node("Income:Salary", 3000)],
      [node("Gastos:Vivienda", 1200)],
      partial,
    );
    const toSavings = data.links.find((l) => l.target === "savings");
    expect(toSavings?.value).toBe(1800);
    expect(data.links.some((l) => l.target === "Gastos:Vivienda")).toBe(true);
  });

  it("classifies and colours accounts by the ledger's root names", () => {
    expect(categorizeAccount("Ingresos:Salario", roots)).toBe("source");
    expect(categorizeAccount("Gastos:Comida", roots)).toBe("operating");
    expect(categorizeAccount("Activos:Banco", roots)).toBe("investing");
    expect(categorizeAccount("Pasivos:Tarjeta", roots)).toBe("financing");
    expect(categorizeAccount("Patrimonio:Apertura", roots)).toBe("exclude");
    expect(categorizeAccount("Income:Salary", roots)).toBe("exclude");
    expect(sankeyRoleForId("Ingresos:Salario", roots)).toBe("source");
    expect(sankeyRoleForId("Gastos:Comida", roots)).toBe("operating");
    expect(isExcludedAccount("Activos:US:BofA:Checking", roots)).toBe(true);
    expect(isExcludedAccount("Assets:Bank:Checking", roots)).toBe(false);
  });

  it("is given the ledger's roots by the card", () => {
    const card = fs
      .readFileSync(
        path.join(
          __dirname,
          "..",
          "screens",
          "reports-screen",
          "components",
          "cash-flow-sankey.tsx",
        ),
        "utf8",
      )
      .replace(/\s+/g, "");
    expect(card.includes("constroots=useLedgerRootNames();")).toBe(true);
    expect(card.includes("roots,}),[income,expenses,roots,t]")).toBe(true);
  });
});
