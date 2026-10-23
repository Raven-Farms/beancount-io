import { amountIn, formatHolding, holdingsOf } from "../balance-display";
import { formatExactUnits, formatUnits, groupThousands } from "../number-utils";

// w21/594: 1.234567890123456789 ETH printed "1.234567890123456690 ETH", because
// the amount was formatted from a double.
describe("amounts needing more than 15 significant digits", () => {
  it("reads a held amount as the ledger wrote it", () => {
    const holding = holdingsOf({ ETH: "1.234567890123456789" })[0];
    expect(formatHolding(holding)).toBe("1.234567890123456789 ETH");
    expect(formatHolding(holding, true)).toBe("+1.234567890123456789 ETH");
    expect(
      formatHolding(holdingsOf({ ETH: "-1234.100000000000000001" })[0]),
    ).toBe("-1,234.100000000000000001 ETH");
  });

  it("keeps the exact text only when a double could not hold it", () => {
    expect(amountIn({ ETH: "1.5" }, "ETH")).toEqual({ number: 1.5, scale: 1 });
    expect(amountIn({ ETH: "597.748" }, "ETH").exact).toBe(undefined);
    expect(amountIn({ ETH: "0.100000000000000000" }, "ETH").exact).toBe(
      "0.100000000000000000",
    );
  });

  it("formats a plain decimal exactly and declines anything else", () => {
    expect(formatExactUnits("0.100000000000000000", "ETH")).toBe(
      "0.100000000000000000 ETH",
    );
    expect(formatExactUnits("-0.000000000000000000", "ETH")).toBe(
      "0.000000000000000000 ETH",
    );
    expect(formatExactUnits("1e-18", "ETH")).toBe(null);
    expect(formatExactUnits("abc", "ETH")).toBe(null);
  });

  it("shows a computed float's untrusted digits as zeros, not as noise", () => {
    expect(formatUnits(0.1, "ETH", 18)).toBe("0.100000000000000000 ETH");
    expect(formatUnits(1.234567890123456789, "ETH", 18)).toBe(
      "1.234567890123460000 ETH",
    );
    expect(groupThousands(0.1 + 0.2, 18)).toBe("0.300000000000000000");
  });

  it("leaves money and ordinary commodities as they were", () => {
    expect(groupThousands(1234.5)).toBe("1,234.50");
    expect(formatUnits(597.748, "RGAGX", 3)).toBe("597.748 RGAGX");
    expect(groupThousands(48471.38532, 5)).toBe("48,471.38532");
  });
});
