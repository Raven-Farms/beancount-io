import { describe, expect, it } from "vitest";
import { isCompleteAccountToken } from "../account-token";
import { buildOpenAccountSchema } from "../open-account-schema";

describe("isCompleteAccountToken", () => {
  it.each([
    "Assets:QaSyntaxDraft",
    "Assets:Emergency-Fund",
    "Assets:401K",
    "Assets:Épargne",
    // w4/279: combining marks (Devanagari, decomposed É) and a titlecase
    // initial, all accepted by the ledger.
    "Assets:Qa-20261020:\u0939\u093F\u0902\u0926\u0940",
    "Assets:Qa-20261020:E\u0301pargne",
    "Assets:Qa-20261020:\u01C5ep",
    "Assets:现金",
  ])("accepts %s", (account) => {
    expect(isCompleteAccountToken(account)).toBe(true);
  });

  it.each([
    "Assets:",
    "Assets::Cash",
    "Assets:Emergency Fund",
    "Assets:Emergency USD",
    "Assets:checking",
    "Assets:\u0301Epargne",
    "Assets:Bank_1",
    "Checking",
    "",
  ])("rejects %s", (account) => {
    expect(isCompleteAccountToken(account)).toBe(false);
  });
});

describe("buildOpenAccountSchema", () => {
  const prefixes = ["Assets", "Liabilities", "Equity", "Income", "Expenses"];
  const schema = buildOpenAccountSchema(prefixes, {
    required: "required",
    mustStartWith: "prefix",
    invalid: (problem) =>
      "component" in problem
        ? `${problem.kind}:${problem.component}`
        : problem.kind,
  });

  it("blocks malformed tokens before a mutation can be prepared", () => {
    expect(
      schema.safeParse({ date: "2026-10-20", account: "Assets:" }).success,
    ).toBe(false);
    expect(
      schema.safeParse({
        date: "2026-10-20",
        account: "Assets:Emergency Fund",
      }).error?.issues[0]?.message,
    ).toBe("whitespace");
  });

  it("keeps the configured-prefix rule and accepts valid names", () => {
    expect(
      schema.safeParse({ date: "2026-10-20", account: "Checking" }).error
        ?.issues[0]?.message,
    ).toBe("prefix");
    expect(
      schema.safeParse({
        date: "2026-10-20",
        account: "Assets:QaSyntaxDraft",
      }).success,
    ).toBe(true);
  });

  it("allows correcting a rejected value into a valid account", () => {
    expect(
      schema.safeParse({ date: "2026-10-20", account: "Assets::Cash" }).success,
    ).toBe(false);
    expect(
      schema.safeParse({
        date: "2026-10-20",
        account: "Assets:Emergency-Fund",
      }).success,
    ).toBe(true);
  });
});

describe("account name reasons (w0/017)", () => {
  const schema = buildOpenAccountSchema(["Assets", "Expenses"], {
    required: "required",
    mustStartWith: "prefix",
    invalid: (problem) =>
      "component" in problem
        ? `${problem.kind}:${problem.component}`
        : problem.kind,
  });
  const message = (account: string) =>
    schema.safeParse({ date: "2026-10-20", account }).error?.issues[0]?.message;

  it("names the actual reason instead of one catch-all", () => {
    expect(message("Assets:bank")).toBe("component-start:bank");
    expect(message("Assets:Bank Account")).toBe("whitespace");
    expect(message("Assets::Bank")).toBe("empty-component");
    expect(message("Assets:Bank:")).toBe("empty-component");
    expect(message("Assets:Bank_1")).toBe("invalid-character:Bank_1");
  });

  it("still accepts Unicode, digit-led and hyphenated components", () => {
    for (const account of [
      "Assets:Café",
      "Assets:1Bank",
      "Expenses:Food:Coffee-Shop",
    ]) {
      expect(message(account), account).toBeUndefined();
    }
  });
});

describe("accounts the ledger already opens (w3/557)", () => {
  const existing = new Map([
    ["Assets:Cash", { openedAt: "2026-01-01", closedAt: null }],
    ["Assets:Old", { openedAt: "2025-01-01", closedAt: "2025-12-31" }],
  ]);
  const schema = buildOpenAccountSchema(
    ["Assets", "Equity"],
    {
      required: "required",
      mustStartWith: "prefix",
      invalid: (problem) => problem.kind,
      exists: (account, { openedAt, closedAt }) =>
        closedAt
          ? `closed:${account}:${closedAt}`
          : `open:${account}:${openedAt}`,
    },
    existing,
  );
  const message = (account: string) =>
    schema.safeParse({ date: "2026-10-20", account }).error?.issues[0]?.message;

  it("refuses an open account and names its open date", () => {
    expect(message("Assets:Cash")).toBe("open:Assets:Cash:2026-01-01");
  });

  it("refuses a closed account, which cannot be reopened", () => {
    expect(message("Assets:Old")).toBe("closed:Assets:Old:2025-12-31");
  });

  it("accepts a new child of an existing account", () => {
    expect(
      schema.safeParse({ date: "2026-10-20", account: "Assets:Cash:Wallet" })
        .success,
    ).toBe(true);
  });

  it("compares names exactly, leaving a case-different root to the prefix rule", () => {
    expect(message("assets:cash")).toBe("prefix");
    expect(
      schema.safeParse({ date: "2026-10-20", account: "Assets:CASH" }).success,
    ).toBe(true);
  });
});
