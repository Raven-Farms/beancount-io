import { firstParams } from "../route-ledger";

// w21/198: a repeated query parameter arrived as an array and crashed the
// screens that called string methods on it.
describe("firstParams", () => {
  it("reduces a repeated param to its first value", () => {
    expect(
      firstParams({ path: ["a.bean", "b.bean"], interval: "monthly" }),
    ).toEqual({ path: "a.bean", interval: "monthly" });
  });

  it("keeps an absent or empty param absent", () => {
    expect(firstParams({ account: undefined, prefill: [] })).toEqual({
      account: undefined,
      prefill: undefined,
    });
  });
});
