import {
  selectTrialBalanceCategories,
  selectTrialBalanceDisplays,
} from "../select-trial-balance";
import { flattenRows } from "../../account-table/flatten-rows";
import { TrialBalanceQuery } from "@/generated-graphql/graphql";

// w21/450: a parent's own euros or shares had no row, and its own commodity
// read as plain dollars.
type Balance = Record<string, string>;
type Node = {
  account: string;
  balance: Balance;
  balanceChildren: Balance;
  children: Node[];
  hasTxns: boolean;
};
const node = (
  account: string,
  balance: Balance,
  balanceChildren: Balance,
  children: Node[] = [],
): Node => ({ account, balance, balanceChildren, children, hasTxns: true });
const empty = (account: string): Node => node(account, {}, {});
const trial = (assets: Node): TrialBalanceQuery =>
  ({
    getLedgerTrialBalance: {
      assetsHierarchyData: assets,
      liabilitiesHierarchyData: empty("Liabilities"),
      equityHierarchyData: empty("Equity"),
      incomeHierarchyData: empty("Income"),
      expensesHierarchyData: empty("Expenses"),
    },
  }) as unknown as TrialBalanceQuery;

const rowsOf = (data: TrialBalanceQuery) =>
  flattenRows(selectTrialBalanceCategories("USD", data), {
    Assets: true,
    "Assets:Bank": true,
    "Assets:Broker": true,
  });

describe("a parent's own postings in another commodity", () => {
  // Assets:Bank holds 500 EUR of its own above a $100 child.
  const euros = trial(
    node("Assets", {}, { USD: "100", EUR: "500" }, [
      node("Assets:Bank", { EUR: "500" }, { USD: "100", EUR: "500" }, [
        node("Assets:Bank:Checking", { USD: "100" }, { USD: "100" }),
      ]),
    ]),
  );

  it("gets an own row, though its operating-currency value is zero", () => {
    const rows = rowsOf(euros);
    const own = rows.find((row) => row.own);
    expect(own?.account).toBe("Assets:Bank");
    expect(own?.value).toBe(0);
  });

  it("shows the euros on that row, as a leaf would", () => {
    const own = rowsOf(euros).find((row) => row.own)!;
    const display = selectTrialBalanceDisplays(
      "USD",
      euros,
      undefined,
      [],
      "2026-10-22",
    ).get(own.key);
    // Its own euros, read in units as a leaf's would be.
    expect(display?.kind).toBe("units");
    expect(
      display?.kind === "units" && [
        display.units.currency,
        display.units.number,
      ],
    ).toEqual(["EUR", 500]);
  });
});

describe("a parent's own shares", () => {
  // Assets:Broker holds 10 VTI of its own, worth $2,500, above a $100 child.
  const valued = trial(
    node("Assets", {}, { USD: "2600" }, [
      node("Assets:Broker", { USD: "2500" }, { USD: "2600" }, [
        node("Assets:Broker:Cash", { USD: "100" }, { USD: "100" }),
      ]),
    ]),
  );
  const units = trial(
    node("Assets", {}, { USD: "100", VTI: "10" }, [
      node("Assets:Broker", { VTI: "10" }, { USD: "100", VTI: "10" }, [
        node("Assets:Broker:Cash", { USD: "100" }, { USD: "100" }),
      ]),
    ]),
  );

  it("reads in units with its value, not as plain dollars", () => {
    const own = rowsOf(valued).find((row) => row.own)!;
    const display = selectTrialBalanceDisplays(
      "USD",
      valued,
      units,
      [],
      "2026-10-22",
    ).get(own.key);
    expect(display?.kind).toBe("units");
    expect(
      display?.kind === "units" && [
        display.units.currency,
        display.units.number,
        display.value?.amount,
      ],
    ).toEqual(["VTI", 10, 2500]);
  });

  it("does not give a parent with nothing of its own an own row", () => {
    const none = trial(
      node("Assets", {}, { USD: "100" }, [
        node("Assets:Bank", {}, { USD: "100" }, [
          node("Assets:Bank:Checking", { USD: "60" }, { USD: "60" }),
          node("Assets:Bank:Savings", { USD: "40" }, { USD: "40" }),
        ]),
      ]),
    );
    expect(rowsOf(none).some((row) => row.own)).toBe(false);
  });
});
