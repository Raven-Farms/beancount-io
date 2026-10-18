import { afterEach, describe, expect, it } from "vitest";
import { rememberReturnPath, takeReturnPath } from "../billing-return";
import { billingSearchSchema } from "../billing-search";

describe("billing return path", () => {
  afterEach(() => window.sessionStorage.clear());

  it("keeps a same-origin path for one read", () => {
    rememberReturnPath("/ledger/alice/books?tab=files");
    expect(takeReturnPath()).toBe("/ledger/alice/books?tab=files");
    expect(takeReturnPath()).toBeNull();
  });

  it.each([
    "https://evil.example/x",
    "//evil.example/x",
    "javascript:alert(1)",
  ])("refuses %s", (path) => {
    rememberReturnPath(path);
    expect(takeReturnPath()).toBeNull();
  });

  it("clears an earlier path when the new purchase has none", () => {
    rememberReturnPath("/ledger/alice/books");
    rememberReturnPath(undefined);
    expect(takeReturnPath()).toBeNull();
  });
});

describe("billing search", () => {
  it("reads Stripe's return and tolerates typos", () => {
    expect(
      billingSearchSchema.parse({ checkout: "SUCCESS", session_id: "cs_1" }),
    ).toMatchObject({ checkout: "success", session_id: "cs_1" });
    expect(billingSearchSchema.parse({ checkout: 1, session_id: 42 })).toEqual({
      checkout: undefined,
      session_id: "42",
      return: undefined,
    });
  });

  it("reads a deep link's plan and cycle, and drops values it does not know", () => {
    expect(
      billingSearchSchema.parse({
        plan: "Growth",
        billing: "YEARLY",
        from: "ai_cfo_panel",
        return: "/ledger/alice/books",
      }),
    ).toMatchObject({
      plan: "growth",
      billing: "yearly",
      from: "ai_cfo_panel",
      return: "/ledger/alice/books",
    });
    expect(
      billingSearchSchema.parse({
        plan: "platinum",
        billing: "weekly",
        return: "https://evil.example/x",
      }),
    ).toMatchObject({ plan: undefined, billing: undefined, return: undefined });
  });
});
