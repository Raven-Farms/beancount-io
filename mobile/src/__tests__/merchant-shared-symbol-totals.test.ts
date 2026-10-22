import { formatMerchantTotals } from "../screens/merchant-detail-screen/selectors/format-merchant-total";

// w21/535: "QA Maple" paid 42.50 USD and 42.50 CAD showed two identical
// "$42.50" total lines.
const total = (currency: string, amount: number) => ({
  currency,
  total: amount,
});

describe("formatMerchantTotals", () => {
  it("tells a USD and a CAD total apart, the ledger's own keeping its symbol", () => {
    const lines = formatMerchantTotals(
      [total("USD", -42.5), total("CAD", -42.5)],
      "USD",
    );
    expect(lines).toEqual(["-$42.50", "-42.50 CAD"]);
    expect(new Set(lines).size).toBe(2);
  });

  it("uses codes for every one when none is the ledger's own", () => {
    expect(
      formatMerchantTotals([total("CAD", -10), total("AUD", -20)], "EUR"),
    ).toEqual(["-10.00 CAD", "-20.00 AUD"]);
  });

  it("tells CNY and JPY apart, and the krone currencies", () => {
    expect(
      formatMerchantTotals([total("CNY", -100), total("JPY", -1500)], "USD"),
    ).toEqual(["-100.00 CNY", "-1,500 JPY"]);
    expect(
      formatMerchantTotals([total("SEK", -1), total("NOK", -2)], "SEK"),
    ).toEqual(["-kr1.00", "-2.00 NOK"]);
  });

  it("leaves a lone total, and totals with distinct symbols, as they were", () => {
    expect(formatMerchantTotals([total("CAD", -42.5)], "USD")).toEqual([
      "-$42.50",
    ]);
    expect(
      formatMerchantTotals([total("USD", -42.5), total("EUR", -10)], "USD"),
    ).toEqual(["-$42.50", "-€10.00"]);
  });

  it("shows a total that rounds to zero unsigned", () => {
    expect(
      formatMerchantTotals([total("USD", 0), total("CAD", -0.001)], "USD"),
    ).toEqual(["$0.00", "0.00 CAD"]);
  });
});
