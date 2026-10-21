import { aggregatePayees } from "../screens/merchants-screen/selectors/aggregate-payees";
import {
  buildMerchantCurrencyTotalsBql,
  buildMerchantMetaBql,
} from "../screens/merchant-detail-screen/selectors/merchant-stats";
import {
  filterExactPayee,
  parseSpellings,
} from "../screens/merchant-detail-screen/selectors/filter-exact-payee";

// w21/046: the directory merged "QA CAFE" and "Qa Cafe" into one row of 3
// transactions, but its detail matched only "QA CAFE": 2 transactions, $9.00,
// and the Oct 3 entry unreachable.
const table = (rows: (string | number)[][]) => ({
  types: [
    { name: "payee", dtype: "str" },
    { name: "transaction_count", dtype: "int" },
    { name: "first_date", dtype: "date" },
    { name: "last_date", dtype: "date" },
  ],
  rows,
});

describe("a merchant spelled more than one way", () => {
  const [merged] = aggregatePayees(
    table([
      ["QA CAFE", 2, "2026-10-01", "2026-10-02"],
      ["Qa Cafe", 1, "2026-10-03", "2026-10-03"],
    ]),
  );

  it("keeps the spellings its directory row merged", () => {
    expect(merged!.payee).toBe("QA CAFE");
    expect(merged!.transactionCount).toBe(3);
    expect(merged!.otherSpellings).toEqual(["Qa Cafe"]);
  });

  it("has no other spellings when it has one", () => {
    const [single] = aggregatePayees(
      table([["Netflix", 4, "2026-01-01", "2026-04-01"]]),
    );
    expect("otherSpellings" in single!).toBe(false);
  });

  it("counts and totals every spelling in the detail's queries", () => {
    const spellings = [merged!.payee, ...merged!.otherSpellings!];
    expect(buildMerchantMetaBql(spellings)).toBe(
      "SELECT count(*) as transaction_count, min(date) as first_date, max(date) as last_date " +
        'FROM #entries WHERE (payee = "QA CAFE" OR payee = "Qa Cafe")',
    );
    expect(
      buildMerchantCurrencyTotalsBql(spellings).includes(
        'WHERE (payee = "QA CAFE" OR payee = "Qa Cafe") AND',
      ),
    ).toBe(true);
    // One spelling keeps the plain predicate.
    expect(
      buildMerchantMetaBql(["Netflix"]).includes('WHERE payee = "Netflix"'),
    ).toBe(true);
  });

  it("lists every spelling's entries and nothing else", () => {
    const entries = [
      { payee: "QA CAFE", n: 1 },
      { payee: "QA CAFE", n: 2 },
      { payee: "Qa Cafe", n: 3 },
      { payee: "QA CAFETERIA", n: 4 },
    ];
    expect(
      filterExactPayee(entries, ["QA CAFE", "Qa Cafe"]).map((e) => e.n),
    ).toEqual([1, 2, 3]);
    expect(filterExactPayee(entries, "QA CAFE").map((e) => e.n)).toEqual([
      1, 2,
    ]);
  });

  it("reads the route's spellings, and ignores anything malformed", () => {
    expect(parseSpellings('["Qa Cafe"]')).toEqual(["Qa Cafe"]);
    expect(parseSpellings(undefined)).toEqual([]);
    expect(parseSpellings("not json")).toEqual([]);
    expect(parseSpellings('{"a":1}')).toEqual([]);
    expect(parseSpellings('["ok", 3]')).toEqual(["ok"]);
  });
});
