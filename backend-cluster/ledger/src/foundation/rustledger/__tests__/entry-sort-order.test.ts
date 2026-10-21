import type { DirectiveJson } from "@rustledger/wasm";
import { restoreEntrySortOrder } from "../entry-sort-order";
import { accountJournalItems } from "../journal-running-balance";

/**
 * w21/134: rustledger hands a day back grouped by kind (balance, pad,
 * transactions, note, event, price, custom), so the account journal walked a
 * salary written before a same-day pad after it: "+100 → 500" and a padding
 * row "+400 → 400". The order below is the real engine's for this source.
 */
const SOURCE = `option "operating_currency" "USD"
2020-01-01 open Assets:Pad USD
2020-01-01 open Income:Salary USD
2026-08-05 * "QA PADSAL"
  Assets:Pad  100.00 USD
  Income:Salary
2026-08-05 note Assets:Pad "n"
2026-08-05 pad Assets:Pad Equity:Opening-Balances
2026-08-05 price EUR 1.10 USD
2026-08-06 balance Assets:Pad 500.00 USD
`;
const open = (account: string): DirectiveJson => ({
  type: "open",
  date: "2020-01-01",
  account,
  currencies: ["USD"],
});
const salary: DirectiveJson = {
  type: "transaction",
  date: "2026-08-05",
  flag: "*",
  narration: "QA PADSAL",
  tags: [],
  links: [],
  postings: [
    { account: "Assets:Pad", units: { number: "100.00", currency: "USD" } },
    { account: "Income:Salary", units: { number: "-100.00", currency: "USD" } },
  ],
};
const note: DirectiveJson = {
  type: "note",
  date: "2026-08-05",
  account: "Assets:Pad",
  comment: "n",
};
const pad: DirectiveJson = {
  type: "pad",
  date: "2026-08-05",
  account: "Assets:Pad",
  source_account: "Equity:Opening-Balances",
};
const price: DirectiveJson = {
  type: "price",
  date: "2026-08-05",
  currency: "EUR",
  amount: { number: "1.10", currency: "USD" },
};
const balance: DirectiveJson = {
  type: "balance",
  date: "2026-08-06",
  account: "Assets:Pad",
  amount: { number: "500.00", currency: "USD" },
};
const ENGINE_ORDER = [
  open("Assets:Pad"),
  open("Income:Salary"),
  pad,
  salary,
  note,
  price,
  balance,
];

describe("restoreEntrySortOrder", () => {
  it("orders a day by Beancount's type rank, then line", () => {
    expect(
      restoreEntrySortOrder(ENGINE_ORDER, { "main.bean": SOURCE }),
    ).toEqual([
      open("Assets:Pad"),
      open("Income:Salary"),
      salary,
      note,
      pad,
      price,
      balance,
    ]);
  });

  it("puts a same-day balance and open first and a close last", () => {
    const close: DirectiveJson = {
      type: "close",
      date: "2026-08-05",
      account: "Assets:Pad",
    };
    const sameDay = { ...balance, date: "2026-08-05" };
    const source = `2026-08-05 close Assets:Pad
2026-08-05 * "QA PADSAL"
  Assets:Pad  100.00 USD
  Income:Salary
2026-08-05 balance Assets:Pad 500.00 USD
`;
    expect(
      restoreEntrySortOrder([sameDay, salary, close], { "main.bean": source }),
    ).toEqual([sameDay, salary, close]);
  });

  it("keeps the engine's order for a day the source does not account for", () => {
    // A plugin-made note has no line of its own.
    const extra = { ...note, comment: "generated" };
    const directives = [pad, salary, note, extra, price];
    expect(restoreEntrySortOrder(directives, { "main.bean": SOURCE })).toEqual(
      directives,
    );
  });

  it("gives the account journal Beancount's running balances", () => {
    const padding: DirectiveJson = {
      ...salary,
      flag: "P",
      narration: "Padding",
      postings: [
        { account: "Assets:Pad", units: { number: "400.00", currency: "USD" } },
        {
          account: "Equity:Opening-Balances",
          units: { number: "-400.00", currency: "USD" },
        },
      ],
    };
    const sorted = restoreEntrySortOrder(ENGINE_ORDER, {
      "main.bean": SOURCE,
    });
    // The engine adapter then inserts each padding row after its pad.
    sorted.splice(sorted.indexOf(pad) + 1, 0, padding);
    expect(
      accountJournalItems(sorted, "Assets:Pad").map((item) => [
        item.entry.type,
        item.change,
        item.balance,
      ]),
    ).toEqual([
      ["open", {}, {}],
      ["transaction", { USD: "100.00" }, { USD: "100.00" }],
      ["note", {}, { USD: "100.00" }],
      ["pad", {}, { USD: "100.00" }],
      ["transaction", { USD: "400.00" }, { USD: "500.00" }],
      ["balance", {}, { USD: "500.00" }],
    ]);
  });
});
