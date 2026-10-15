import { describe, expect, it } from "vitest";
import type { SerializableTreeNode } from "@/graphql/definitions";
import { sumBalanceRecords } from "@/features/reports/export/model";
import { mergeIntervalAccountChanges } from "../merge-intervals";
import {
  buildCashFlowStatement,
  CashFlowReconciliationError,
  collectCashAccounts,
  type IntervalAccountChanges,
} from "../model";
import {
  cashTransferPayload,
  convertedSalePayload,
} from "./fixtures/converted-sale";

function buildPayload(
  payload:
    | ReturnType<typeof convertedSalePayload>
    | ReturnType<typeof cashTransferPayload>,
) {
  return buildCashFlowStatement({
    intervals: mergeIntervalAccountChanges(
      payload.incomeIntervals,
      payload.expenseIntervals,
      payload.assetIntervals,
      payload.liabilityIntervals,
      payload.equityIntervals,
    ),
    closingCashAccounts: collectCashAccounts(
      payload.getLedgerBalanceSheet.assetsHierarchyData as SerializableTreeNode,
    ),
    primaryCurrency: "USD",
  });
}

function rejection(intervals: IntervalAccountChanges[]) {
  try {
    buildCashFlowStatement({
      intervals,
      closingCashAccounts: [],
      primaryCurrency: "USD",
    });
  } catch (error) {
    expect(error).toBeInstanceOf(CashFlowReconciliationError);
    return error as CashFlowReconciliationError;
  }
  throw new Error("Expected non-conserving movements to be rejected");
}

describe("cash flow reconciliation precondition", () => {
  it("retains the public At Cost sale's independently verified cash movement and opening", () => {
    const statement = buildPayload(convertedSalePayload("at_cost"));
    expect(statement.netChange).toEqual({ USD: "905.05" });
    expect(statement.opening).toEqual({ USD: "27390.30" });
    expect(statement.closing).toEqual({ USD: "28295.35" });
    expect(statement.intervals[0].net).toEqual({ USD: "905.05" });
  });

  it.each([
    ["at_value", { USD: "60.00" }],
    ["units", { USD: "1045.00", NWRB: "-100" }],
  ] as const)(
    "rejects the actual public %s security maps despite unchanged cash",
    (conversion, differences) => {
      const payload = convertedSalePayload(conversion);
      expect(
        payload.assetIntervals[0].accountBalances["Assets:Brokerage:Cash"],
      ).toEqual({ USD: "905.05" });
      const error = rejection(
        mergeIntervalAccountChanges(
          payload.expenseIntervals,
          payload.assetIntervals,
        ),
      );
      expect(error.date).toBe("2026-05-12");
      expect(error.differences).toEqual(differences);
    },
  );

  it("rejects opposite discrepancies in separate chart intervals even when the period sum is zero", () => {
    const intervals: IntervalAccountChanges[] = [
      {
        date: "2026-05-01",
        accountChanges: { "Expenses:Fees": { USD: "60" } },
      },
      {
        date: "2026-06-01",
        accountChanges: { "Income:Refund": { USD: "-60" } },
      },
    ];
    expect(
      sumBalanceRecords(
        intervals.flatMap((point) => Object.values(point.accountChanges)),
      ),
    ).toEqual({ USD: "0" });
    expect(rejection(intervals).date).toBe("2026-05-01");
  });

  it("keeps units independent when their numbers would cancel", () => {
    const error = rejection([
      {
        date: "2026-05-01",
        accountChanges: {
          "Expenses:Fees": { USD: "100" },
          "Assets:Bank:Checking": { EUR: "-100" },
        },
      },
    ]);
    expect(error.differences).toEqual({ USD: "100", EUR: "-100" });
  });

  it("tolerates Beancount's per-posting balancing residual and nothing more (w0/022)", () => {
    // Three postings allow up to 0.015 USD: the half-cent per posting a
    // balanced Beancount transaction may leave. Exact decimals, no floats.
    const accepted = buildCashFlowStatement({
      intervals: [
        {
          date: "2026-05-01",
          accountChanges: {
            "Expenses:Fees": { USD: "0.1" },
            "Income:Salary": { USD: "-0.3" },
            "Assets:Bank:Checking": { USD: "0.214" },
          },
        },
      ],
      closingCashAccounts: [],
      primaryCurrency: "USD",
    });
    expect(accepted.intervals).toHaveLength(1);

    const error = rejection([
      {
        date: "2026-05-01",
        accountChanges: {
          "Expenses:Fees": { USD: "0.1" },
          "Income:Salary": { USD: "-0.3" },
          "Assets:Bank:Checking": { USD: "0.216" },
        },
      },
    ]);
    expect(error.differences).toEqual({ USD: "0.016" });
  });

  it("accepts the public example's at-cost monthly residuals across a year", () => {
    // Bucket residuals measured on open_ledger/example at_cost, time=2016:
    // each interval leaves sub-cent tolerance residue, booked to
    // Equity:Conversions:Current only in the last bucket.
    const residuals = ["0.00057", "0.00426", "-0.0099", "0.00192", "-0.00638"];
    const intervals: IntervalAccountChanges[] = residuals.map(
      (residual, index) => ({
        date: `2016-0${index + 1}-28`,
        accountChanges: {
          "Expenses:Food": { USD: "100" },
          "Income:Salary": { USD: "-500" },
          "Assets:US:Vanguard:RGAGX": { USD: "250" },
          "Assets:US:BofA:Checking": {
            USD: (150 + Number(residual)).toFixed(5),
          },
        },
      }),
    );
    expect(() =>
      buildCashFlowStatement({
        intervals,
        closingCashAccounts: [],
        primaryCurrency: "USD",
      }),
    ).not.toThrow();
  });

  it("accepts exact mixed-scale decimal conservation including zero-only units", () => {
    const statement = buildCashFlowStatement({
      intervals: [
        {
          date: "2026-05-01",
          accountChanges: {
            "Expenses:Fees": { USD: "0.1", EUR: "-0.00" },
            "Income:Salary": { USD: "-0.3" },
            "Assets:Bank:Checking": { USD: "0.20000000000000000000" },
          },
        },
      ],
      closingCashAccounts: [],
      primaryCurrency: "USD",
    });
    expect(statement.netChange).toEqual({ USD: "0.2", EUR: "0.00" });
  });

  it("rejects a filtered sale whose cash counterpart is absent", () => {
    const payload = convertedSalePayload("at_cost");
    delete (
      payload.assetIntervals[0].accountBalances as Record<string, unknown>
    )["Assets:Brokerage:Cash"];
    expect(() => buildPayload(payload)).toThrow(CashFlowReconciliationError);
  });

  it("keeps the public cash-only transfer valid without activity or invented cash movement", () => {
    const statement = buildPayload(cashTransferPayload());
    expect(statement.rows).toEqual([]);
    expect(statement.netChange).toEqual({});
    expect(statement.closing).toEqual({ USD: "60000" });
    expect(statement.opening).toEqual({ USD: "60000" });
    expect(statement.intervals[0].net).toEqual({});
  });
});
