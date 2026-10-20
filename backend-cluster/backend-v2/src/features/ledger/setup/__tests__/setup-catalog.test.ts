import { presetById, setupCatalog, setupCurrencies, setupFixtures } from "..";

const EXPECTED_PRESETS = [
  "personal@1",
  "freelance@1",
  "business@1",
  "portfolio@1",
  "rental@1",
  "shared-expenses@1",
  "community@1",
  "blank@1",
];

describe("setup catalog (w3/m53/t001)", () => {
  it("freezes every ADR021 preset at version 1", () => {
    expect(setupCatalog.presets.map((preset) => preset.id)).toEqual(
      EXPECTED_PRESETS,
    );
    for (const preset of setupCatalog.presets) {
      expect(preset.version).toBe(1);
      expect(presetById(preset.id)).toBe(preset);
    }
  });

  it("keeps the zero-to-two optional-question budget per preset", () => {
    for (const preset of setupCatalog.presets) {
      expect(preset.optionalQuestions.length).toBeLessThanOrEqual(2);
      const ids = preset.optionalQuestions.map((question) => question.id);
      expect(new Set(ids).size).toBe(ids.length);
      for (const question of preset.optionalQuestions) {
        expect(question.prompt.length).toBeGreaterThan(0);
        expect(question.effect.length).toBeGreaterThan(0);
      }
    }
    expect(presetById("blank@1")?.optionalQuestions).toEqual([]);
    expect(presetById("blank@1")?.accounts).toEqual([]);
  });

  it("names Accounts uniquely within each preset and marks the review account reachable", () => {
    for (const preset of setupCatalog.presets) {
      const names = preset.accounts.map((account) => account.name);
      expect(new Set(names).size).toBe(names.length);
      for (const question of preset.optionalQuestions) {
        for (const enabled of question.enablesAccounts) {
          expect(enabled).toMatch(/^(Assets|Liabilities|Income|Expenses|Equity):/);
        }
      }
    }
  });

  it("carries a first result, teaching examples, and an acceptance scenario per preset", () => {
    for (const preset of setupCatalog.presets) {
      expect(preset.firstResult.length).toBeGreaterThan(0);
      expect(preset.teachingExamples.length).toBeGreaterThanOrEqual(3);
      expect(Object.keys(preset.acceptanceScenario.expected).length).toBeGreaterThan(0);
    }
  });
});

describe("setup currency tables", () => {
  it("lists active ISO 4217 alphabetic codes", () => {
    expect(setupCurrencies.supportedCurrencies).toContain("USD");
    expect(setupCurrencies.supportedCurrencies).toContain("EUR");
    expect(setupCurrencies.supportedCurrencies.length).toBeGreaterThan(150);
    for (const code of setupCurrencies.supportedCurrencies) {
      expect(code).toMatch(/^[A-Z]{3}$/);
    }
  });

  it("maps a region only when CLDR lists exactly one current currency", () => {
    const supported = new Set(setupCurrencies.supportedCurrencies);
    for (const [region, currency] of Object.entries(
      setupCurrencies.regionCurrency,
    )) {
      expect(region).toMatch(/^[A-Z]{2}$/);
      expect(supported.has(currency)).toBe(true);
    }
    // Multi-currency or currency-less regions have no row (ADR021).
    for (const region of ["AQ", "BT", "HT", "LS", "NA", "PA", "PS", "ZW"]) {
      expect(setupCurrencies.regionCurrency[region]).toBeUndefined();
    }
    expect(setupCurrencies.regionCurrency.US).toBe("USD");
    expect(setupCurrencies.regionCurrency.DE).toBe("EUR");
    expect(setupCurrencies.regionCurrency.GB).toBe("GBP");
    expect(setupCurrencies.regionCurrency.JP).toBe("JPY");
  });
});

describe("setup conformance fixtures", () => {
  it("covers every preset with a clean and an acceptance fixture", () => {
    for (const id of EXPECTED_PRESETS) {
      expect(
        setupFixtures.some((fixture) => fixture.id === `${id}-clean`),
      ).toBe(true);
      expect(
        setupFixtures.some((fixture) => fixture.id === `${id}-acceptance`),
      ).toBe(true);
    }
  });

  it("distinguishes unknown, zero, and known opening states", () => {
    const byId = new Map(setupFixtures.map((fixture) => [fixture.id, fixture]));
    const known = byId.get("personal@1-opening-known");
    const zero = byId.get("personal@1-opening-zero");
    const unknown = byId.get("personal@1-opening-unknown");
    expect(known?.expected).toMatchObject({
      openingTransactionDate: "2026-01-31",
      balanceAssertionDate: "2026-02-01",
    });
    expect(zero?.expected).toMatchObject({ verifiedZero: true });
    // An unknown balance must never read as a verified zero.
    expect(unknown?.expected).toMatchObject({ verifiedZero: false });
  });
});
