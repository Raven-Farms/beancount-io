import { buildBudgetEntry, isBudgetAmount } from "../build-budget-entry";
import { budgetDirection } from "../selectors/budget-selectors";

describe("buildBudgetEntry", () => {
  const base = {
    account: "Expenses:Food:Groceries",
    interval: "MONTHLY",
    number: "500",
    currency: "USD",
    date: new Date(2026, 7, 9),
  };

  it("dates the entry by the local calendar, not a UTC-shifted day", () => {
    // Late local evening in a negative-offset zone rolls forward under
    // toISOString(); the shared formatter must not.
    const entry = buildBudgetEntry({
      ...base,
      date: new Date(2026, 0, 31, 23, 30),
    });

    expect(entry.budget?.date).toBe("2026-01-31");
  });

  it("builds the budget entry the schema expects", () => {
    expect(buildBudgetEntry(base)).toEqual({
      type: "BUDGET",
      budget: {
        account: "Expenses:Food:Groceries",
        interval: "MONTHLY",
        date: "2026-08-09",
        amount: { number: "500", currency: "USD" },
      },
    });
  });

  it("preserves a negative amount, which declares an income target", () => {
    const entry = buildBudgetEntry({ ...base, number: "-5000" });

    expect(entry.budget?.amount.number).toBe("-5000");
  });

  it("passes decimals through verbatim rather than coercing to a number", () => {
    const entry = buildBudgetEntry({ ...base, number: "1234.50" });

    expect(entry.budget?.amount.number).toBe("1234.50");
  });

  it("normalizes stray whitespace and casing from the form", () => {
    const entry = buildBudgetEntry({
      ...base,
      account: "  Expenses:Food  ",
      currency: " usd ",
      number: " 500 ",
      interval: "monthly",
    });

    expect(entry.budget?.account).toBe("Expenses:Food");
    expect(entry.budget?.amount.currency).toBe("USD");
    expect(entry.budget?.amount.number).toBe("500");
    expect(String(entry.budget?.interval)).toBe("MONTHLY");
  });

  describe("on an account under the ledger's income root", () => {
    const income = { ...base, account: "Income:Salary", incomeRoot: "Income" };

    it("stores a positively typed amount as an income target", () => {
      const entry = buildBudgetEntry({ ...income, number: "5000" });

      expect(entry.budget?.amount.number).toBe("-5000");
      expect(budgetDirection(Number(entry.budget?.amount.number))).toBe(-1);
    });

    it("keeps an amount already typed negative, and decimals verbatim", () => {
      expect(
        buildBudgetEntry({ ...income, number: "-5000" }).budget?.amount.number,
      ).toBe("-5000");
      expect(
        buildBudgetEntry({ ...income, number: "+1234.50" }).budget?.amount
          .number,
      ).toBe("-1234.50");
    });

    it("follows a localized root and nested accounts, not a name prefix", () => {
      expect(
        buildBudgetEntry({
          ...base,
          account: "Einnahmen:Gehalt:Bonus",
          incomeRoot: "Einnahmen",
          number: "300",
        }).budget?.amount.number,
      ).toBe("-300");
      expect(
        buildBudgetEntry({
          ...base,
          account: "IncomeTax:Refund",
          incomeRoot: "Income",
        }).budget?.amount.number,
      ).toBe("500");
    });

    it("leaves expense budgets, and any budget without a known root, as typed", () => {
      expect(
        buildBudgetEntry({ ...base, incomeRoot: "Income" }).budget?.amount
          .number,
      ).toBe("500");
      expect(
        buildBudgetEntry({ ...income, incomeRoot: undefined, number: "5000" })
          .budget?.amount.number,
      ).toBe("5000");
    });
  });
});

describe("isBudgetAmount", () => {
  // Add Budget enabled Done for any non-empty text and wrote it verbatim, so
  // `12..3`, `abc` or `1 000` committed an unparsable `custom "budget"` line
  // (w0/038).
  it("accepts plain decimal amounts, signed or not", () => {
    for (const text of ["500", "-50", "+12", "0.5", "49.99", " 500 ", "0"]) {
      expect(isBudgetAmount(text)).toBe(true);
    }
  });

  it("refuses text the ledger cannot parse as a number", () => {
    for (const text of [
      "12..3",
      "abc",
      "1 000",
      "1,000",
      "$500",
      "1e3",
      ".5",
      "12.",
      "-",
      "",
      "   ",
    ]) {
      expect(isBudgetAmount(text)).toBe(false);
    }
  });

  it("gates Add Budget's Done and names the problem under the field", () => {
    const source = require("fs").readFileSync(
      require("path").join(
        __dirname,
        "..",
        "..",
        "add-budget-screen",
        "add-budget-screen.tsx",
      ),
      "utf8",
    ) as string;
    expect(source.includes("const amountOk = isBudgetAmount(amount);")).toBe(
      true,
    );
    const guard = source.match(/const canSubmit =[\s\S]*?;/);
    expect(guard?.[0].includes("amountOk")).toBe(true);
    expect(guard?.[0].includes("amount.trim().length > 0")).toBe(false);
    expect(source.includes('{t("budgetAmountInvalid")}')).toBe(true);
  });
});
