import fs from "fs";
import path from "path";
import { en } from "../../../translations/en";

// w21/104: a credit card's balance was entered as a positive opening balance
// and stored that way, and the decimal pad had no minus to type otherwise.
describe("Create Ledger's opening amount for a liability", () => {
  const source = fs.readFileSync(
    path.join(__dirname, "..", "create-ledger-screen.tsx"),
    "utf8",
  );

  it("asks for the amount owed when a Liabilities account is chosen", () => {
    expect(en.createLedgerAmountOwed).toBe("Amount owed (optional)");
    expect(
      source.includes(
        'const openingAmountLabelKey = openingAccountValue.startsWith("Liabilities:")',
      ),
    ).toBe(true);
    expect(
      source.includes("accessibilityLabel={t(openingAmountLabelKey)}"),
    ).toBe(true);
  });

  it("offers a keypad that can type a minus", () => {
    expect(source.includes('keyboardType="decimal-pad"')).toBe(false);
    expect(source.includes('"numbers-and-punctuation"')).toBe(true);
  });
});
