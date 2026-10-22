import { translationLocales } from "./locale-parity";

// w21/584: translations that said something else than the English they stand for.
// eslint-disable-next-line @typescript-eslint/no-require-imports
const catalogOf = (locale: string) => require(`../${locale}`)[locale];

describe("translation meaning fixes", () => {
  it("zh: the amount hint says the sign button switches positive and negative, not income and expense", () => {
    const hint: string = catalogOf("zh").postingAmountHint;
    expect(hint.includes("收支")).toBe(false);
    expect(hint.includes("正数和负数")).toBe(true);
  });

  it("sk: an unconfirmed write is 'not confirmed', not 'refused'", () => {
    const text: string = catalogOf("sk").ledgerWriteUnconfirmed;
    expect(text.startsWith("Server nepotvrdil uloženie.")).toBe(true);
    expect(text.includes("neprijal")).toBe(false);
  });

  it("uk: the Rental preset speaks of a refundable deposit, not a returned one", () => {
    const text: string = catalogOf("uk").createLedgerPresetRentalOutcome;
    expect(text.includes("зворотної застави")).toBe(true);
    expect(text.includes("поверненої")).toBe(false);
  });

  it("every language's re-enter message names the Decide later button by its own label", () => {
    for (const locale of translationLocales()) {
      const catalog = catalogOf(locale);
      expect(
        catalog.createLedgerAmountReenter.includes(
          catalog.createLedgerOpeningNone,
        ),
      ).toBe(true);
    }
  });
});
