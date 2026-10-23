import { describe, it, expect } from "vitest";
import { SETUP_PRESETS, suggestCurrency } from "../setup-presets";
import { LedgerSetupPreset } from "@/graphql/definitions";

describe("setup presets", () => {
  it("lists every catalog preset exactly once", () => {
    expect(SETUP_PRESETS.map((preset) => preset.id).sort()).toEqual(
      Object.values(LedgerSetupPreset).sort(),
    );
  });

  it("suggests currency from the region, never the language", () => {
    expect(suggestCurrency("en-US")).toBe("USD");
    expect(suggestCurrency("en-GB")).toBe("GBP");
    expect(suggestCurrency("de-DE")).toBe("EUR");
    expect(suggestCurrency("fr-FR")).toBe("EUR");
    expect(suggestCurrency("ja-JP")).toBe("JPY");
    // A language with no region subtag names no currency zone.
    expect(suggestCurrency("de")).toBe("USD");
    expect(suggestCurrency(undefined)).toBe("USD");
  });
});
