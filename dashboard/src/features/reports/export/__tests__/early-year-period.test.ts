import { describe, expect, it } from "vitest";
import type { SerializableTreeNode } from "@/graphql/definitions";
import { buildStatementFilename, statementToCSV } from "../csv";
import { statementToMarkdown } from "../markdown";
import {
  buildBalanceSheetDocument,
  buildProfitAndLossDocument,
} from "../model";
import {
  parseConcreteTimeFilter,
  resolveReportingPeriod,
} from "../reporting-period";

/** Years below 100 are real calendar years, not 1900–1999 (w4/283). */
describe("early-year statement periods", () => {
  it.each([
    ["0099-08", "0099-08-01", "0099-08-31"],
    ["0100-08", "0100-08-01", "0100-08-31"],
    ["0001", "0001-01-01", "0001-12-31"],
    ["0099-Q4", "0099-10-01", "0099-12-31"],
    ["0004-02", "0004-02-01", "0004-02-29"],
    ["0099-12-15 - 0100-01-15", "0099-12-15", "0100-01-15"],
    ["0099-W52", "0099-12-21", "0099-12-27"],
    ["FY0100", "0099-04-01", "0100-03-31"],
  ])("resolves %s to %s – %s", (selection, startDate, endDate) => {
    expect(
      parseConcreteTimeFilter(
        selection,
        selection.startsWith("FY") ? { month: 3, day: 31 } : undefined,
      ),
    ).toEqual({ startDate, endDate });
  });

  it.each(["0099-02-29", "0003-02-29", "0099-13", "0099-W54"])(
    "still refuses the impossible %s",
    (selection) => {
      expect(parseConcreteTimeFilter(selection)).toBeNull();
    },
  );

  it.each(["profit_and_loss", "cash_flow"] as const)(
    "gives a %s statement its explicit early-year bounds",
    (kind) => {
      expect(
        resolveReportingPeriod({
          kind,
          timeFilter: "0099-08",
          reportDates: ["0099-08-31"],
          generatedOn: "2026-10-20",
          interval: "monthly",
        }),
      ).toEqual({
        startDate: "0099-08-01",
        endDate: "0099-08-31",
        asOfDate: null,
        isExplicit: true,
        selection: "0099-08",
      });
    },
  );

  it("still leaves a relative selection unresolved", () => {
    expect(
      resolveReportingPeriod({
        kind: "profit_and_loss",
        timeFilter: "year-1",
        reportDates: ["0099-08-31"],
        generatedOn: "2026-10-20",
      }).isExplicit,
    ).toBe(false);
  });

  const node = (
    account: string,
    balance: Record<string, unknown>,
  ): SerializableTreeNode => ({
    __typename: "SerializableTreeNode",
    account,
    balance,
    balanceChildren: balance,
    children: [],
    cost: null,
    costChildren: null,
    hasTxns: true,
  });
  const context = {
    reportingEntity: "QA Books",
    reportingEntitySource: "ledger_title" as const,
    ledgerName: "QA Books",
    primaryCurrency: "USD",
    conversion: "units" as const,
    interval: "monthly" as const,
    filters: {
      time: "0099-08",
      account: "Expenses:Qa-20261020:Period-Export",
      filter: "",
    },
    reportDates: ["0099-08-31"],
    generatedAt: "2026-10-20T12:00:00.000Z",
  };

  it("dates the Income Statement CSV, Markdown and filename", () => {
    const document = buildProfitAndLossDocument({
      ...context,
      title: "Income Statement",
      income: node("Income", {}),
      expenses: node("Expenses", { USD: "3.75" }),
      netProfitBalances: [{ USD: "3.75" }],
      labels: { income: "Income", expenses: "Expenses", net_profit: "Net" },
    });

    const [header, ...rows] = statementToCSV(document).trim().split(/\r?\n/);
    const columns = header.split(",");
    for (const row of rows) {
      const cells = row.split(",");
      expect(cells[columns.indexOf("period_start")]).toBe("0099-08-01");
      expect(cells[columns.indexOf("period_end")]).toBe("0099-08-31");
      expect(cells[columns.indexOf("period_is_explicit")]).toBe("true");
    }
    expect(buildStatementFilename(document)).toContain(
      "0099-08-01-to-0099-08-31",
    );
    const markdown = statementToMarkdown(document, {
      locale: "en-US",
      t: (key) => key,
    });
    expect(markdown).not.toContain("reportingDateUnavailable");
    expect(markdown).toMatch(/August 1.*99/);
  });

  it("dates the Balance Sheet as of the early-year end", () => {
    const document = buildBalanceSheetDocument({
      ...context,
      title: "Balance Sheet",
      assets: node("Assets", { USD: "1" }),
      liabilities: node("Liabilities", {}),
      equity: node("Equity", { USD: "-1" }),
      labels: {
        assets: "Assets",
        liabilities: "Liabilities",
        equity: "Equity",
      },
    });

    expect(document.context.reportingPeriod.asOfDate).toBe("0099-08-31");
    expect(buildStatementFilename(document)).toContain("0099-08-31");
  });
});
