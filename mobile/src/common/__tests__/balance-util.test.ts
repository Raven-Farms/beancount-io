import { resolveCurrencyBalance } from "../balance-util";

describe("resolveCurrencyBalance", () => {
  it("returns 0 for null/undefined maps", () => {
    expect(resolveCurrencyBalance(null, "USD")).toBe(0);
    expect(resolveCurrencyBalance(undefined, "USD")).toBe(0);
  });

  it("uses the requested currency when present", () => {
    expect(resolveCurrencyBalance({ USD: 100, EUR: 90 }, "EUR")).toBe(90);
  });

  // w21/058: the USD entry used to stand in, then printed with the active
  // currency's symbol.
  it("reads 0, never the USD entry, when the currency is missing", () => {
    expect(resolveCurrencyBalance({ USD: 100, EUR: 90 }, "CNY")).toBe(0);
    expect(resolveCurrencyBalance({ USD: "50.00" }, "EUR")).toBe(0);
    expect(resolveCurrencyBalance({ EUR: "200.00", USD: "50.00" }, "EUR")).toBe(
      200,
    );
    expect(resolveCurrencyBalance({}, "EUR")).toBe(0);
  });

  it("returns 0 when neither the currency nor USD is present", () => {
    expect(resolveCurrencyBalance({ EUR: 90 }, "CNY")).toBe(0);
  });

  it("parses string amounts", () => {
    expect(resolveCurrencyBalance({ USD: "1500.50" }, "USD")).toBe(1500.5);
  });

  it("treats invalid strings as 0", () => {
    expect(resolveCurrencyBalance({ USD: "not-a-number" }, "USD")).toBe(0);
  });

  it("does not fall back for a present zero value (uses the `in` check)", () => {
    expect(resolveCurrencyBalance({ USD: 0, EUR: 90 }, "USD")).toBe(0);
  });

  it("passes through negative numbers", () => {
    expect(resolveCurrencyBalance({ USD: -250.25 }, "USD")).toBe(-250.25);
  });
});
