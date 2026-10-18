import { describe, expect, it } from "vitest";
import { billingLinkSearch } from "../billing-link";

describe("billingLinkSearch", () => {
  it("opens a plan on yearly by default and keeps the way back", () => {
    expect(
      billingLinkSearch({
        from: "ledgers_limit",
        plan: "growth",
        returnTo: "/ledger/alice/books?view=journal#top",
      }),
    ).toEqual({
      plan: "growth",
      billing: "yearly",
      from: "ledgers_limit",
      return: "/ledger/alice/books?view=journal#top",
    });
  });

  it("keeps the cycle a prompt quoted", () => {
    expect(
      billingLinkSearch({
        from: "ai_cfo_panel",
        plan: "premium",
        billing: "monthly",
      }),
    ).toEqual({ plan: "premium", billing: "monthly", from: "ai_cfo_panel" });
  });

  it("opens Billing without a sheet when no plan is recommended", () => {
    expect(billingLinkSearch({ from: "directive_usage" })).toEqual({
      from: "directive_usage",
    });
  });
});
