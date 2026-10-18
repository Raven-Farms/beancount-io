import { describe, expect, it } from "vitest";
import {
  applyAutoBalanceToPostings,
  computeAutoBalance,
  findUnbalancedResiduals,
  findUnresolvedEligibleAmount,
} from "../transaction-auto-balance";

describe("computeAutoBalance", () => {
  it("ignores unused blank-account rows when inferring a residual", () => {
    const result = computeAutoBalance(
      [
        { account: "", amount: "100", currency: "MUSD" },
        { account: "Expenses:Cost", amount: "10", currency: "MUSD" },
        { account: "Assets:Cash", amount: "", currency: "MUSD" },
        { account: "", amount: "", currency: "MUSD" },
      ],
      "MUSD",
    );

    expect(result.incomplete).toBe(false);
    expect(result.balances.get(2)?.amount).toBe("-10");
    expect(result.balances.has(0)).toBe(false);
  });

  it("rejects multiple blank eligible amounts instead of inventing NaN", () => {
    const result = computeAutoBalance(
      [
        { account: "Expenses:A", amount: "10", currency: "MUSD" },
        { account: "Assets:Cash", amount: "", currency: "MUSD" },
        { account: "Expenses:B", amount: "", currency: "MUSD" },
      ],
      "MUSD",
    );

    expect(result.incomplete).toBe(true);
    expect(result.balances.size).toBe(0);
  });

  it("infers a single missing amount per currency including zeros", () => {
    const sameCurrency = computeAutoBalance(
      [
        { account: "A", amount: "10", currency: "MUSD" },
        { account: "B", amount: "-4", currency: "MUSD" },
        { account: "C", amount: "", currency: "MUSD" },
      ],
      "MUSD",
    );
    expect(sameCurrency.incomplete).toBe(false);
    expect(sameCurrency.balances.get(2)?.amount).toBe("-6");

    const zeros = computeAutoBalance(
      [
        { account: "A", amount: "0", currency: "MUSD" },
        { account: "B", amount: "0", currency: "MUSD" },
        { account: "C", amount: "", currency: "MUSD" },
      ],
      "MUSD",
    );
    expect(zeros.balances.get(2)?.amount).toBe("0");

    const multi = computeAutoBalance(
      [
        { account: "A", amount: "10", currency: "MUSD" },
        { account: "B", amount: "", currency: "MUSD" },
        { account: "C", amount: "5", currency: "USD" },
        { account: "D", amount: "", currency: "USD" },
      ],
      "MUSD",
    );
    expect(multi.incomplete).toBe(false);
    expect(multi.balances.get(1)?.amount).toBe("-10");
    expect(multi.balances.get(3)?.amount).toBe("-5");
  });

  it.each<[string[], string]>([
    [["0.1", "0.2"], "-0.3"],
    [["-0.12345", "0.00005"], "0.12340"],
    [["0.00000001"], "-0.00000001"],
    [["12345678901234567890"], "-12345678901234567890"],
    [["10.25"], "-10.25"],
  ])("infers the exact decimal residual of %j as %j", (filled, expected) => {
    const postings = [
      ...filled.map((amount, index) => ({
        account: `Expenses:Item${index}`,
        amount,
        currency: "BTC",
      })),
      { account: "Assets:Wallet", amount: "", currency: "BTC" },
    ];
    const result = computeAutoBalance(postings, "BTC");

    expect(result.balances.get(filled.length)?.amount).toBe(expected);
  });
});

describe("applyAutoBalanceToPostings", () => {
  it("fills only eligible empty amounts and keeps precise fractional text", () => {
    const balances = new Map([[1, { amount: "-0.0001", currency: "MUSD" }]]);
    const next = applyAutoBalanceToPostings(
      [
        { account: "Expenses:A", amount: "0.0001", currency: "MUSD" },
        { account: "Assets:Cash", amount: "", currency: "MUSD" },
        { account: "", amount: "", currency: "MUSD" },
      ],
      balances,
    );

    expect(next[1].amount).toBe("-0.0001");
    expect(next[2].amount).toBe("");
    expect(findUnresolvedEligibleAmount(next)).toBeNull();
  });

  it("detects unresolved eligible amounts after failed inference", () => {
    expect(
      findUnresolvedEligibleAmount([
        { account: "A", amount: "10", currency: "MUSD" },
        { account: "B", amount: "", currency: "MUSD" },
        { account: "C", amount: "", currency: "MUSD" },
      ]),
    ).toBe(1);
  });

  it("treats a value that is not a decimal number as unresolved", () => {
    expect(
      findUnresolvedEligibleAmount([
        { account: "A", amount: "12abc", currency: "MUSD" },
        { account: "B", amount: "-12", currency: "MUSD" },
      ]),
    ).toBe(0);
  });
});

describe("findUnbalancedResiduals", () => {
  const posting = (account: string, amount: string, currency = "USD") => ({
    account,
    amount,
    currency,
  });

  it("names the residual of postings that do not sum to zero", () => {
    expect(
      findUnbalancedResiduals(
        [posting("Expenses:Food", "10"), posting("Assets:Cash", "-9")],
        "USD",
      ),
    ).toEqual([{ amount: "1", currency: "USD" }]);
  });

  it("accepts postings that balance, decimals summed exactly", () => {
    expect(
      findUnbalancedResiduals(
        [
          posting("Expenses:A", "0.1"),
          posting("Expenses:B", "0.2"),
          posting("Assets:Cash", "-0.3"),
        ],
        "USD",
      ),
    ).toEqual([]);
  });

  it("accepts an inferred amount once it is applied", () => {
    const postings = [
      posting("Expenses:Food", "10"),
      posting("Assets:Cash", ""),
    ];
    const { balances } = computeAutoBalance(postings, "USD");

    expect(
      findUnbalancedResiduals(
        applyAutoBalanceToPostings(postings, balances),
        "USD",
      ),
    ).toEqual([]);
  });

  it("checks each currency on its own", () => {
    expect(
      findUnbalancedResiduals(
        [
          posting("Expenses:Food", "10", "USD"),
          posting("Assets:Cash", "-10", "USD"),
          posting("Expenses:Travel", "5", "EUR"),
          posting("Assets:Wallet", "-4.50", "EUR"),
        ],
        "USD",
      ),
    ).toEqual([{ amount: "0.50", currency: "EUR" }]);
  });

  it("groups a blank currency under the primary currency", () => {
    expect(
      findUnbalancedResiduals(
        [posting("Expenses:Food", "10", ""), posting("Assets:Cash", "-10")],
        "USD",
      ),
    ).toEqual([]);
  });

  it.each([
    // Half the last place of the least precise amount: 0.005.
    ["10.00", "-9.996", false],
    ["10.00", "-9.995", false],
    ["10.00", "-9.994", true],
    ["10.00", "-9.99", true],
    // The least precise decimal wins: 10.00 tolerates 0.005 beside -9.999.
    ["10.00", "-9.999", false],
    // Only the decimal amount infers a tolerance, 0.00005 here.
    ["10", "-9.9999", true],
    ["10", "-10.0", false],
    // Integers infer none.
    ["10", "-10", false],
    ["1000000", "-999999", true],
  ])("%s with %s is unbalanced: %s", (first, second, unbalanced) => {
    const residuals = findUnbalancedResiduals(
      [posting("Expenses:Food", first), posting("Assets:Cash", second)],
      "USD",
    );
    expect(residuals.length > 0).toBe(unbalanced);
  });

  it("ignores unused rows and leaves unparseable amounts to the resolver", () => {
    expect(
      findUnbalancedResiduals(
        [
          posting("Expenses:Food", "10"),
          posting("Assets:Cash", "-10"),
          posting("", "7"),
          posting("Expenses:Other", "abc"),
        ],
        "USD",
      ),
    ).toEqual([]);
  });
});
