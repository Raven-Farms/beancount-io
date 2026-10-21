import {
  filterFlowSeriesByRange,
  flowAnchorMonth,
} from "../../../../common/series-util";
import { selectAccountTransactions } from "../select-account-transactions";
import { selectStatementAnchorMonth } from "../select-income-expense-chart";
import { selectRangedAccountTree } from "../select-ranged-account-tree";
import {
  DirectiveType,
  JournalDirectiveType,
} from "../../../transactions-screen/types";

/**
 * w21/166: one pre-entered rent cheque for November moved every Reports range
 * onto November, so "1M" on 21 October showed only November.
 */
const TODAY_MONTH = "2026-10";
const expenses = [
  { date: "2026-09-30", value: 10 },
  { date: "2026-10-31", value: 40 },
  { date: "2026-11-30", value: 1500 },
];

describe("Reports ranges with a future-dated entry", () => {
  it("end on the current month, never a future one", () => {
    expect(flowAnchorMonth("2026-11", TODAY_MONTH)).toBe("2026-10");
    expect(
      filterFlowSeriesByRange(expenses, "1M", TODAY_MONTH).map((p) => p.date),
    ).toEqual(["2026-10-31"]);
    expect(
      filterFlowSeriesByRange(expenses, "3M", TODAY_MONTH).map((p) => p.date),
    ).toEqual(["2026-09-30", "2026-10-31"]);
    expect(filterFlowSeriesByRange(expenses, "ALL", TODAY_MONTH)).toEqual(
      expenses,
    );
  });

  it("still show a stale ledger's last active months", () => {
    const stale = [
      { date: "2025-05-31", value: 1 },
      { date: "2025-06-30", value: 2 },
    ];
    expect(
      filterFlowSeriesByRange(stale, "1M", TODAY_MONTH).map((p) => p.date),
    ).toEqual(["2025-06-30"]);
  });

  it("anchor Recent transactions on October, without November's rent", () => {
    const anchor = selectStatementAnchorMonth(TODAY_MONTH, [
      { date: "2026-10-31", balance: {} },
      { date: "2026-11-30", balance: {} },
    ]);
    expect(anchor).toBe("2026-10");
    const entry = (date: string, hash: string) =>
      ({
        entry_hash: hash,
        date,
        directive_type: DirectiveType.TRANSACTION,
        flag: "*",
        payee: null,
        narration: null,
        tags: [],
        links: [],
        postings: [
          {
            account: "Expenses:Transport",
            units: { number: "40", currency: "USD" },
          },
        ],
      }) as unknown as JournalDirectiveType;
    expect(
      selectAccountTransactions(
        [entry("2026-10-14", "bus"), entry("2026-11-01", "rent")],
        "Expenses",
        "1M",
        anchor,
      ).map((e) => e.entry_hash),
    ).toEqual(["bus"]);
  });

  it("leave next month out of the breakdowns", () => {
    const { total } = selectRangedAccountTree(
      "USD",
      [
        {
          date: "2026-10-31",
          accountBalances: { "Expenses:Transport": { USD: 40 } },
        },
        {
          date: "2026-11-30",
          accountBalances: { "Expenses:Housing:Rent": { USD: 1500 } },
        },
      ],
      "1M",
      "expenses",
      TODAY_MONTH,
    );
    expect(total).toBe(40);
  });
});
