import { detectRecurrence } from "../screens/merchants-screen/selectors/detect-recurrence";
import {
  buildPayeeSeriesBql,
  mapPayeeSeries,
  payeeSeriesCutoff,
  shiftLedgerMonths,
  PAYEE_SERIES_WINDOW_MONTHS,
} from "../screens/merchants-screen/selectors/payee-series";
import type { QueryResultTableLike } from "../screens/merchants-screen/selectors/bql-table";

const TYPES = [
  { name: "txn_date", dtype: "date" },
  { name: "payee", dtype: "str" },
  { name: "amount", dtype: "Decimal" },
  { name: "currency", dtype: "str" },
];

function table(rows: unknown[][], types = TYPES): QueryResultTableLike {
  return { rows, types };
}

describe("buildPayeeSeriesBql", () => {
  it("is the fixed aliased series statement with an interpolated cutoff", () => {
    const bql = buildPayeeSeriesBql("2023-07-20");
    expect(bql.includes("txn_date")).toBe(true);
    expect(bql.includes("number as amount")).toBe(true);
    expect(bql.includes("payee != ''")).toBe(true);
    expect(bql.includes("account ~ '^Expenses'")).toBe(true);
    expect(bql.includes("date >= 2023-07-20")).toBe(true);
  });
});

describe("shiftLedgerMonths / payeeSeriesCutoff", () => {
  it("shifts calendar months and clamps end-of-month days", () => {
    expect(shiftLedgerMonths("2026-08-20", -PAYEE_SERIES_WINDOW_MONTHS)).toBe(
      "2023-07-20",
    );
    expect(shiftLedgerMonths("2024-01-31", -1)).toBe("2023-12-31");
    expect(shiftLedgerMonths("2024-03-31", -1)).toBe("2024-02-29");
    expect(shiftLedgerMonths("nope", -1)).toBe(null);
  });

  it("derives the series cutoff from today", () => {
    expect(payeeSeriesCutoff("2026-08-20")).toBe("2023-07-20");
  });
});

describe("mapPayeeSeries", () => {
  it("groups points by payee and sorts by date", () => {
    const mapped = mapPayeeSeries(
      table([
        ["2024-03-01", "Netflix", "-15.99", "USD"],
        ["2024-01-01", "Netflix", "-15.99", "USD"],
        ["2024-02-01", "Spotify", "-10.99", "USD"],
        ["2024-02-01", "Netflix", "-15.99", "USD"],
      ]),
    );
    expect([...mapped.keys()].sort()).toEqual(["Netflix", "Spotify"]);
    expect(mapped.get("Netflix")!.map((p) => p.date)).toEqual([
      "2024-01-01",
      "2024-02-01",
      "2024-03-01",
    ]);
  });

  it("resolves columns by name regardless of order", () => {
    const reordered = [
      { name: "currency", dtype: "str" },
      { name: "payee", dtype: "str" },
      { name: "txn_date", dtype: "date" },
      { name: "amount", dtype: "Decimal" },
    ];
    const mapped = mapPayeeSeries(
      table([["USD", "Netflix", "2024-01-01", "-15.99"]], reordered),
    );
    expect(mapped.get("Netflix")).toEqual([
      { date: "2024-01-01", currency: "USD", amount: -15.99 },
    ]);
  });

  it("sums same-day same-currency amounts for one payee", () => {
    const mapped = mapPayeeSeries(
      table([
        ["2024-12-31", "Corp", "100", "USD"],
        ["2024-12-31", "Corp", "50", "USD"],
        ["2024-12-31", "Corp", "-10", "EUR"],
      ]),
    );
    expect(mapped.get("Corp")).toEqual([
      { date: "2024-12-31", currency: "EUR", amount: -10 },
      { date: "2024-12-31", currency: "USD", amount: 150 },
    ]);
  });

  it("returns an empty map for null/missing columns/bad cells", () => {
    expect(mapPayeeSeries(null).size).toBe(0);
    expect(
      mapPayeeSeries(
        table(
          [["2024-01-01", "X", "-1", "USD"]],
          [
            { name: "txn_date", dtype: "date" },
            { name: "payee", dtype: "str" },
          ],
        ),
      ).size,
    ).toBe(0);
    expect(
      mapPayeeSeries(
        table([
          [null, "Netflix", "-1", "USD"],
          ["2024-01-01", "", "-1", "USD"],
          ["2024-01-01", "Netflix", "nope", "USD"],
          ["2024-01-01", "Netflix", "-1", null],
        ]),
      ).size,
    ).toBe(0);
  });
});

// w21/173: a payee that is only ever a transfer never entered the series,
// so it was never detected and a manual mark read "Not enough history".
describe("a payee that is only ever a transfer", () => {
  const WITH_ACCOUNT = [...TYPES, { name: "account", dtype: "str" }];
  const saturdays = [
    "2026-09-05",
    "2026-09-12",
    "2026-09-19",
    "2026-09-26",
    "2026-10-03",
    "2026-10-10",
    "2026-10-17",
  ];

  it("reads its debited legs, and is detected weekly", () => {
    const mapped = mapPayeeSeries(
      table(
        saturdays.map((date) => [
          date,
          "ATM Withdrawal",
          "100.00",
          "USD",
          "Assets:Cash",
        ]),
        WITH_ACCOUNT,
      ),
    );
    const series = mapped.get("ATM Withdrawal")!;
    expect(series.length).toBe(7);
    const verdict = detectRecurrence(series, "2026-10-21");
    expect(verdict?.cadence).toBe("weekly");
    expect(verdict?.typicalAmountByCurrency.USD).toBe(100);
    expect(verdict?.nextExpected).toBe("2026-10-24");
  });

  it("keeps a payee's Expenses legs when it has them", () => {
    const mapped = mapPayeeSeries(
      table(
        [
          ["2026-10-01", "Grocer", "40.00", "USD", "Expenses:Food"],
          // A refund's debited cash leg is not the payee's spending.
          ["2026-10-02", "Grocer", "5.00", "USD", "Assets:Cash"],
        ],
        WITH_ACCOUNT,
      ),
    );
    expect(mapped.get("Grocer")!.map((p) => p.amount)).toEqual([40]);
  });

  // w21/334: one ATM fee (an Expenses leg) anywhere in the window made the
  // payee read money legs only, which left a one-event series.
  it("keeps the transfer series when a single fee leg is on file", () => {
    const rows = [
      ...saturdays.map((date) => [
        date,
        "QA SWEEP",
        "100.00",
        "USD",
        "Assets:Cash",
      ]),
      ["2026-07-03", "QA SWEEP", "2.50", "USD", "Expenses:Bank:Fees"],
      // And a fee on a day that also has a transfer.
      ["2026-10-10", "QA SWEEP", "2.50", "USD", "Expenses:Bank:Fees"],
    ];
    const series = mapPayeeSeries(table(rows, WITH_ACCOUNT)).get("QA SWEEP")!;
    expect(series.length).toBe(7);
    expect(series.every((point) => point.amount === 100)).toBe(true);
    const verdict = detectRecurrence(series, "2026-10-21");
    expect(verdict?.cadence).toBe("weekly");
    expect(verdict?.typicalAmountByCurrency.USD).toBe(100);
    expect(verdict?.isApproximate).toBe(false);
  });

  it("still prefers the money legs when they cover more days", () => {
    const rows = [
      ["2026-10-01", "Grocer", "40.00", "USD", "Expenses:Food"],
      ["2026-10-08", "Grocer", "45.00", "USD", "Expenses:Food"],
      ["2026-10-02", "Grocer", "5.00", "USD", "Assets:Cash"],
    ];
    expect(
      mapPayeeSeries(table(rows, WITH_ACCOUNT))
        .get("Grocer")!
        .map((p) => p.amount),
    ).toEqual([40, 45]);
  });

  it("asks for debited legs alongside the money legs", () => {
    const bql = buildPayeeSeriesBql("2023-07-20");
    expect(bql.includes(", account WHERE")).toBe(true);
    expect(bql.includes(" OR number > 0)")).toBe(true);
  });
});
