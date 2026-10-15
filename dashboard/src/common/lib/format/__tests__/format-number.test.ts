import { describe, it, expect } from "vitest";
import { formatNumber } from "../format-number";

describe("formatNumber", () => {
  it("uses the supplied locale for thousands separators", () => {
    expect(formatNumber(80149.807, true, "en")).toBe("80,149.807");
    // ICU spells the French group separator with a narrow no-break space whose
    // exact code point moves between versions; the decimal comma does not.
    expect(formatNumber(80149.807, true, "fr")).toMatch(/^80.149,807$/);
  });

  it("ignores the runtime default locale", () => {
    // The regression this guards: `toLocaleString()` with no locale formats
    // with the browser's preference, so a server render and a French browser's
    // hydration disagree and React throws away the server-rendered report.
    const original = Number.prototype.toLocaleString;
    Number.prototype.toLocaleString = function (
      this: number,
      locale?: Intl.LocalesArgument,
      options?: Intl.NumberFormatOptions,
    ) {
      return original.call(this, locale ?? "fr", options);
    };
    try {
      expect(formatNumber(80149.807, true, "en")).toBe("80,149.807");
    } finally {
      Number.prototype.toLocaleString = original;
    }
  });

  it("omits separators when renderCommas is false, regardless of locale", () => {
    expect(formatNumber(1234567.89, false, "fr")).toBe("1234567.89");
    expect(formatNumber(1234567, false, "fr")).toBe("1234567");
  });

  it("strips trailing zeros without separators", () => {
    expect(formatNumber(1.5, false, "en")).toBe("1.5");
    expect(formatNumber(1.004, false, "en")).toBe("1");
  });
});

describe("formatNumber with a currency (w0/010)", () => {
  it("writes an ISO currency at its minor-unit precision", () => {
    expect(formatNumber(4559.8, true, "en", "USD")).toBe("4,559.80");
    expect(formatNumber(109529.339, true, "en", "USD")).toBe("109,529.34");
    expect(formatNumber(-2095.6, true, "en", "USD")).toBe("-2,095.60");
    expect(formatNumber(1200, true, "en", "JPY")).toBe("1,200");
    expect(formatNumber(1.2345, true, "en", "KWD")).toBe("1.235");
  });

  it("lets render_commas change grouping only, not precision", () => {
    expect(formatNumber(48471.38532, true, "en", "USD")).toBe("48,471.39");
    expect(formatNumber(48471.38532, false, "en", "USD")).toBe("48471.39");
  });

  it("keeps source-driven formatting for non-ISO commodities", () => {
    expect(formatNumber(1346.683, true, "en", "MUSD")).toBe("1,346.683");
    expect(formatNumber(64, true, "en", "VHT")).toBe("64");
    expect(formatNumber(-13, true, "en", "VACHR")).toBe("-13");
    expect(formatNumber(0.5, true, "en", "BTC")).toBe("0.5");
  });

  it("never prints a negative zero for a sub-cent residue", () => {
    expect(formatNumber(-0.003, true, "en", "USD")).toBe("0.00");
    expect(formatNumber(-0.005, true, "en", "USD")).toBe("-0.01");
  });

  it("is unchanged without a currency", () => {
    expect(formatNumber(4559.8, true, "en")).toBe("4,559.8");
  });
});
