import { SETUP_PRESETS, suggestCurrency } from "../setup-presets";

describe("setup presets", () => {
  it("lists every catalog preset exactly once", () => {
    expect(SETUP_PRESETS.map((preset) => String(preset.id)).sort()).toEqual([
      "BLANK",
      "BUSINESS",
      "COMMUNITY",
      "FREELANCE",
      "PERSONAL",
      "PORTFOLIO",
      "RENTAL",
      "SHARED_EXPENSES",
    ]);
  });

  it("suggests currency from the region only", () => {
    expect(suggestCurrency("US")).toBe("USD");
    expect(suggestCurrency("GB")).toBe("GBP");
    expect(suggestCurrency("DE")).toBe("EUR");
    expect(suggestCurrency("JP")).toBe("JPY");
    expect(suggestCurrency(null)).toBe("USD");
    expect(suggestCurrency("XX")).toBe("USD");
  });
});
