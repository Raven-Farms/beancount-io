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

// w21/093: a padded "QA STARBUX " was trimmed into "QA STARBUX", so the
// detail's exact statements counted 2 of the 3 rows it listed.
describe("a merchant spelled with trailing whitespace", () => {
  const [merged] = aggregatePayees(
    table([
      ["QA STARBUX", 2, "2026-08-24", "2026-08-25"],
      ["QA STARBUX ", 1, "2026-08-26", "2026-08-26"],
    ]),
  );

  it("keeps both spellings, showing the trimmed one", () => {
    expect(merged!.payee).toBe("QA STARBUX");
    expect(merged!.transactionCount).toBe(3);
    expect(merged!.otherSpellings).toEqual(["QA STARBUX "]);
  });

  it("counts the padded rows in the detail's statements", () => {
    const spellings = [merged!.payee, ...merged!.otherSpellings!];
    expect(
      buildMerchantMetaBql(spellings).includes(
        '(payee = "QA STARBUX" OR payee = "QA STARBUX ")',
      ),
    ).toBe(true);
    expect(
      buildMerchantCurrencyTotalsBql(spellings).includes(
        'payee = "QA STARBUX "',
      ),
    ).toBe(true);
  });

  it("survives the route param", () => {
    expect(parseSpellings(JSON.stringify(merged!.otherSpellings))).toEqual([
      "QA STARBUX ",
    ]);
  });
});

// w21/410: a decomposed "Café" and a composed one look the same and are two
// strings, so Merchants listed two identical-looking rows with half the history.
describe("a merchant spelled composed and decomposed", () => {
  const NFC = "Café Central";
  const NFD = "Café Central";
  const data = table([
    [NFC, 1, "2026-10-01", "2026-10-01"],
    [NFD, 1, "2026-10-05", "2026-10-05"],
  ]);

  it("is one merchant with both transactions and both spellings kept", () => {
    expect(NFC.length === NFD.length).toBe(false);
    const merchants = aggregatePayees(data);
    expect(merchants.length).toBe(1);
    expect(merchants[0].transactionCount).toBe(2);
    expect(
      [merchants[0].payee, ...(merchants[0].otherSpellings ?? [])].sort(),
    ).toEqual([NFC, NFD].sort());
    expect(merchants[0].lastDate).toBe("2026-10-05");
  });

  it("is found by a search typed in either form", () => {
    const {
      filterMerchants,
    } = require("../screens/merchants-screen/selectors/aggregate-payees");
    const merchants = aggregatePayees(data);
    expect(filterMerchants(merchants, "café").length).toBe(1);
    expect(filterMerchants(merchants, "café").length).toBe(1);
  });

  it("shares one merchant key, so recurrence sees the whole history", () => {
    const { merchantKey } = require("../common/merchant-key");
    expect(merchantKey(NFC)).toBe(merchantKey(NFD));
    expect(merchantKey(` ${NFD} `)).toBe(merchantKey(NFC.toUpperCase()));
  });
});

// w21/460: double spaces from bank imports split one merchant in two, and a
// search found only one of them.
describe("a merchant with runs of whitespace in its payee", () => {
  const data = table([
    ["Whole Foods", 5, "2026-01-01", "2026-05-01"],
    ["Whole  Foods", 3, "2026-06-01", "2026-08-01"],
    ["WHOLE FOODS", 1, "2026-09-01", "2026-09-01"],
    ["Whole Foods", 2, "2026-09-05", "2026-09-20"],
  ]);

  it("is one merchant with every transaction and spelling kept", () => {
    const merchants = aggregatePayees(data);
    expect(merchants.length).toBe(1);
    expect(merchants[0].transactionCount).toBe(11);
    expect(merchants[0].payee).toBe("Whole Foods");
    expect(merchants[0].otherSpellings?.length).toBe(3);
  });

  it("is found by a search for either spelling", () => {
    const {
      filterMerchants,
    } = require("../screens/merchants-screen/selectors/aggregate-payees");
    const merchants = aggregatePayees(data);
    expect(filterMerchants(merchants, "whole foods").length).toBe(1);
    expect(filterMerchants(merchants, "whole   foods").length).toBe(1);
    expect(filterMerchants(merchants, "foods").length).toBe(1);
  });

  it("shares one merchant key", () => {
    const { merchantKey } = require("../common/merchant-key");
    expect(merchantKey("Whole  Foods")).toBe(merchantKey("whole foods"));
    expect(merchantKey("  Whole \t Foods ")).toBe("whole foods");
  });
});
