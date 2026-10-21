import {
  SETUP_PRESETS,
  suggestCurrency,
  defaultHistoryStart,
  openingAmountValue,
} from "../setup-presets";

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

// w21/051: Books begin defaulted to the UTC date, so an evening ledger in the
// Americas began tomorrow and the first entry dated today was refused.
describe("defaultHistoryStart", () => {
  it("is the device's own date at 23:30 in America/Los_Angeles", () => {
    const zone = process.env.TZ;
    process.env.TZ = "America/Los_Angeles";
    try {
      const evening = new Date(2026, 9, 20, 23, 30);
      expect(evening.toISOString().slice(0, 10)).toBe("2026-10-21");
      expect(defaultHistoryStart(evening)).toBe("2026-10-20");
    } finally {
      if (zone === undefined) delete process.env.TZ;
      else process.env.TZ = zone;
    }
  });
});

describe("openingAmountValue", () => {
  it("accepts the decimal comma the decimal pad offers", () => {
    expect(openingAmountValue("1234,56")).toBe("1234.56");
    expect(openingAmountValue("1234.56")).toBe("1234.56");
    expect(openingAmountValue("-25")).toBe("-25");
  });

  it("leaves an empty field empty and refuses anything else", () => {
    expect(openingAmountValue("  ")).toBe("");
    expect(openingAmountValue("12,3,4")).toBe(null);
    expect(openingAmountValue("abc")).toBe(null);
  });
});

describe("Create Ledger's Preset option", () => {
  it("has its own description, not the Review step's", () => {
    const screen = require("fs").readFileSync(
      require("path").join(__dirname, "..", "create-ledger-screen.tsx"),
      "utf8",
    ) as string;
    expect(screen.includes('"createLedgerStartPresetHint"')).toBe(true);
    expect(screen.includes('"createLedgerReviewDescription",\n')).toBe(false);
  });
});
