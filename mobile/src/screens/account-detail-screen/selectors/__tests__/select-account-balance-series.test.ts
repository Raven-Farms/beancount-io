import {
  selectAccountBalanceDisplay,
  selectAccountBalanceSeries,
  selectAccountUnitsSeries,
} from "../select-account-balance-series";
import { AccountReportQuery } from "@/generated-graphql/graphql";
import {
  balanceSeriesBaseline,
  filterBalanceSeriesByRange,
  type TimeRange,
} from "../../../../common/series-util";

function createReport(
  linechartData: Array<{
    date: string;
    balance: Record<string, number | string>;
  }>,
): AccountReportQuery {
  return {
    getLedgerAccountReport: { linechartData },
  } as unknown as AccountReportQuery;
}

describe("selectAccountBalanceSeries", () => {
  it("returns an empty array when data is undefined", () => {
    expect(selectAccountBalanceSeries("USD", undefined)).toEqual([]);
  });

  it("converts an account's linechart data into a monthly balance series", () => {
    const data = createReport([
      { date: "2025-02-01", balance: { USD: 320 } },
      { date: "2025-01-01", balance: { USD: 300 } },
    ]);
    expect(selectAccountBalanceSeries("USD", data)).toEqual([
      { date: "2025-01-01", value: 300 },
      { date: "2025-02-01", value: 320 },
    ]);
  });
});

describe("selectAccountBalanceDisplay", () => {
  // Assets:US:Vanguard:RGAGX in `open_ledger/example`, whose last change is on
  // 2017-08-14; the ledger's prices run to 2017-09-08.
  const market = createReport([
    { date: "2017-07-31", balance: { USD: "49331.926" } },
    { date: "2017-08-14", balance: { USD: "48656.6872" } },
  ]);
  const units = createReport([
    { date: "2017-07-31", balance: { RGAGX: "585" } },
    { date: "2017-08-14", balance: { RGAGX: "597.748" } },
  ]);
  const prices = [
    {
      base: "RGAGX",
      quote: "USD",
      prices: [{ date: "2017-08-11" }, { date: "2017-09-08" }],
    },
  ];
  const TODAY = "2026-09-26";

  it("values one commodity as its Accounts row does, at the latest price", () => {
    expect(
      selectAccountBalanceDisplay("USD", market, units, prices, TODAY, {
        USD: "48471.38532",
      }),
    ).toEqual({
      kind: "units",
      units: { currency: "RGAGX", number: 597.748, scale: 3 },
      value: { amount: 48471.38532, basis: "market" },
      notInTotal: [],
    });
  });

  it("falls back to the report's latest point until the row's read lands", () => {
    expect(
      selectAccountBalanceDisplay("USD", market, units, prices, TODAY),
    ).toEqual({
      kind: "units",
      units: { currency: "RGAGX", number: 597.748, scale: 3 },
      value: { amount: 48656.6872, basis: "market" },
      notInTotal: [],
    });
  });

  it("reads a commodity without a price at cost", () => {
    const display = selectAccountBalanceDisplay(
      "USD",
      market,
      units,
      [],
      TODAY,
      { USD: "49049.66613" },
    );
    expect(display.kind === "units" && display.value).toEqual({
      amount: 49049.66613,
      basis: "cost",
    });
  });

  // w21/179: the header was the report's point, priced on the account's last
  // posting date, while its Accounts row read today's value.
  it("values a money total today, as its Accounts row does", () => {
    // Assets:US:Vanguard: two funds and a cent of cash.
    const display = selectAccountBalanceDisplay(
      "USD",
      createReport([{ date: "2017-08-14", balance: { USD: "89045.42238" } }]),
      createReport([
        {
          date: "2017-08-14",
          balance: { USD: "-0.02", RGAGX: "597.748", VBMPX: "193.442" },
        },
      ]),
      [
        ...prices,
        { base: "VBMPX", quote: "USD", prices: [{ date: "2017-08-11" }] },
      ],
      TODAY,
      { USD: "88000" },
    );
    expect(display.kind).toBe("money");
    const valuation = display.kind === "money" ? display.valuation : undefined;
    // The row's figure, valued at the latest prices, and checked against
    // today: RGAGX's newest price is years old by then.
    expect(display.kind === "money" && display.value).toBe(88000);
    expect(valuation?.priced[0]?.priceDate).toBe("2017-09-08");
    expect(valuation?.priced[0]?.stale).toBe(true);
  });

  it("is an empty money figure before either report arrives", () => {
    const display = selectAccountBalanceDisplay(
      "USD",
      undefined,
      undefined,
      undefined,
      TODAY,
    );
    expect(display.kind).toBe("money");
    expect(display.kind === "money" && display.value).toBe(0);
    expect(display.kind === "money" && display.valuation?.valuesHoldings).toBe(
      false,
    );
  });
});

describe("selectAccountUnitsSeries", () => {
  it("charts the commodity's units month by month", () => {
    const data = createReport([
      { date: "2017-07-31", balance: { RGAGX: "585" } },
      { date: "2017-08-14", balance: { RGAGX: "597.748" } },
    ]);
    expect(selectAccountUnitsSeries("RGAGX", data)).toEqual([
      { date: "2017-07-31", value: 585 },
      { date: "2017-08-14", value: 597.748 },
    ]);
  });

  it("reads a month without the commodity as zero, never its cash", () => {
    const data = createReport([{ date: "2017-01-31", balance: { USD: 250 } }]);
    expect(selectAccountUnitsSeries("RGAGX", data)).toEqual([
      { date: "2017-01-31", value: 0 },
    ]);
    // Nor does the money series read cash in another currency (w21/058).
    expect(selectAccountBalanceSeries("EUR", data)[0].value).toBe(0);
  });
});

// w21/125: the units chart took the latest balance's scale, so a round
// "1000" after 999.50 + 0.50 showed August's 0.5 as "1".
describe("selectAccountUnitsScale", () => {
  const {
    selectAccountUnitsScale,
  } = require("../select-account-balance-series");
  it("takes the widest scale across the series", () => {
    const data = {
      getLedgerAccountReport: {
        linechartData: [
          { date: "2026-08-31", balance: { BTC: "0.5" } },
          { date: "2026-09-30", balance: { BTC: "1" } },
          { date: "2026-10-31", balance: { BTC: "1.00000050" } },
        ],
      },
    };
    expect(selectAccountUnitsScale("BTC", data)).toBe(8);
    expect(selectAccountUnitsScale("BTC", undefined)).toBe(0);
  });

  it("is what account detail formats its chart with", () => {
    const source = require("fs").readFileSync(
      require("path").join(__dirname, "..", "..", "account-detail-screen.tsx"),
      "utf8",
    ) as string;
    expect(
      source.includes(
        "formatUnits(value, unitsCurrency, chartScale, includePlus)",
      ),
    ).toBe(true);
  });
});

// w21/164: the ledger sends points only where the balance changed, and the
// chart spaces them by index, so a dormant month vanished.
describe("a month with no postings", () => {
  it("repeats the balance it closed with, dated its last day", () => {
    const data = createReport([
      { date: "2026-08-05", balance: { USD: "2000" } },
      { date: "2026-10-12", balance: { USD: "1500" } },
    ]);
    expect(selectAccountBalanceSeries("USD", data)).toEqual([
      { date: "2026-08-05", value: 2000 },
      { date: "2026-09-30", value: 2000 },
      { date: "2026-10-12", value: 1500 },
    ]);
  });

  it("fills across a year end, in units too", () => {
    const data = createReport([
      { date: "2025-11-20", balance: { ITOT: "3" } },
      { date: "2026-02-02", balance: { ITOT: "5" } },
    ]);
    expect(
      selectAccountUnitsSeries("ITOT", data).map((point) => point.date),
    ).toEqual(["2025-11-20", "2025-12-31", "2026-01-31", "2026-02-02"]);
  });
});

// w21/179: a mixed cash-and-holdings account's header was its last point,
// priced on its last posting date, not today as its Accounts row is.
describe("a mixed account's balance today", () => {
  const report = createReport([
    { date: "2026-09-02", balance: { USD: "1000" } },
  ]);

  it("ends the series on today's value", () => {
    expect(
      selectAccountBalanceSeries("USD", report, {
        balance: { USD: "1250" },
        today: "2026-10-21",
      }),
    ).toEqual([
      { date: "2026-09-02", value: 1000 },
      { date: "2026-10-21", value: 1250 },
    ]);
    // Across a dormant month, the month in between closes on the old value.
    expect(
      selectAccountBalanceSeries("USD", report, {
        balance: { USD: "1250" },
        today: "2026-11-21",
      }).map((point) => point.date),
    ).toEqual(["2026-09-02", "2026-10-31", "2026-11-21"]);
  });

  it("replaces a point already in this month", () => {
    const thisMonth = createReport([
      { date: "2026-10-05", balance: { USD: "1000" } },
    ]);
    expect(
      selectAccountBalanceSeries("USD", thisMonth, {
        balance: { USD: "1250" },
        today: "2026-10-21",
      }),
    ).toEqual([{ date: "2026-10-21", value: 1250 }]);
  });

  it("is unchanged without a current value", () => {
    expect(selectAccountBalanceSeries("USD", report)).toEqual([
      { date: "2026-09-02", value: 1000 },
    ]);
  });
});

// w21/240: windows counted back from an account's last posting, not from today,
// so a Savings account last moved in March read "+$500.00" over 1M in October.
describe("a quiet account over the recent ranges", () => {
  const today = "2026-10-21";
  const report = createReport([
    { date: "2026-02-03", balance: { USD: 1000 } },
    { date: "2026-03-05", balance: { USD: 1500 } },
  ]);
  const change = (
    series: ReturnType<typeof selectAccountBalanceSeries>,
    range: TimeRange,
  ) => {
    const windowed = filterBalanceSeriesByRange(series, range, 2026);
    return (
      windowed[windowed.length - 1].value -
      balanceSeriesBaseline(series, range, 2026)
    );
  };

  it("reads no change over 1M, 3M and 6M, and the whole rise over 1Y", () => {
    // No trial-balance value for the account: its last balance holds.
    const series = selectAccountBalanceSeries("USD", report, undefined, today);
    expect(series[series.length - 1]).toEqual({ date: today, value: 1500 });
    for (const range of ["1M", "3M", "6M"] as const) {
      expect(change(series, range)).toBe(0);
    }
    expect(change(series, "1Y")).toBe(1500);
  });

  it("does the same when today's value is known", () => {
    const series = selectAccountBalanceSeries(
      "USD",
      report,
      { balance: { USD: 1500 }, today },
      today,
    );
    for (const range of ["1M", "3M", "6M"] as const) {
      expect(change(series, range)).toBe(0);
    }
    expect(change(series, "1Y")).toBe(1500);
  });

  it("carries a commodity's held units to today too", () => {
    const units = createReport([
      { date: "2026-02-03", balance: { VTI: 10 } },
      { date: "2026-03-05", balance: { VTI: 15 } },
    ]);
    const series = selectAccountUnitsSeries("VTI", units, today);
    expect(series[series.length - 1]).toEqual({ date: today, value: 15 });
    expect(change(series, "3M")).toBe(0);
    expect(change(series, "1Y")).toBe(15);
  });

  it("leaves an account that moved this month, and callers without a day, as they were", () => {
    const active = createReport([
      { date: "2026-09-02", balance: { USD: 100 } },
      { date: "2026-10-05", balance: { USD: 150 } },
    ]);
    const series = selectAccountBalanceSeries("USD", active, undefined, today);
    expect(series[series.length - 1]).toEqual({
      date: "2026-10-05",
      value: 150,
    });
    expect(change(series, "1M")).toBe(50);
    expect(selectAccountBalanceSeries("USD", report).length).toBe(2);
    expect(selectAccountUnitsSeries("VTI", undefined, today)).toEqual([]);
  });
});
