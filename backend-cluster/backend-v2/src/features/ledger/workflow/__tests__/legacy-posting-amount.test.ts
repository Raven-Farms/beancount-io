import fs from "fs";
import path from "path";
import { parsePostingAmount } from "../legacy-posting-amount";
import { LegacyEntryWorkflow } from "../legacy-entry-workflow";
import { BadUserInputError } from "@/shared/errors";

// w21/190: only exactly three uppercase letters parsed, so "11.11 MUSD" fell
// back to a bare number in USD and every save on such a ledger was refused.
describe("parsePostingAmount", () => {
  it.each([
    ["11.11 MUSD", "11.11", "MUSD"],
    ["-11.11 USDC", "-11.11", "USDC"],
    ["5.00 VBTLX", "5.00", "VBTLX"],
    ["3.00 A1B", "3.00", "A1B"],
    ["1,000.25 EUR", "1000.25", "EUR"],
    ["-7 USD", "-7", "USD"],
    ["2 X", "2", "X"],
    ["0.5 BRK.B", "0.5", "BRK.B"],
    ["10 HOOL_2026", "10", "HOOL_2026"],
  ])("reads %s", (amount, number, currency) => {
    expect(parsePostingAmount(amount)).toEqual({ number, currency });
  });

  it("refuses an amount with no currency instead of assuming USD", () => {
    for (const amount of ["100", "", "abc USD", "5 usd", "5 1ABC", "5 EUR-"]) {
      expect(() => parsePostingAmount(amount)).toThrow(BadUserInputError);
    }
  });

  it("is what the legacy workflow parses a posting's amount with", () => {
    expect(typeof LegacyEntryWorkflow).toBe("function");
    const source = fs.readFileSync(
      path.join(__dirname, "..", "legacy-entry-workflow.ts"),
      "utf8",
    );
    expect(source.includes("units: parsePostingAmount(posting.amount)")).toBe(
      true,
    );
  });
});
