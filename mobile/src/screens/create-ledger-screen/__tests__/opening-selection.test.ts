import fs from "fs";
import path from "path";
import { openingSelection, SETUP_PRESETS } from "../setup-presets";

// w21/106: a typed opening balance was dropped under "Decide later", and an
// account picked under one preset was still sent under another.
const accountsOf = (id: string) =>
  SETUP_PRESETS.find((preset) => preset.id === id)!.accounts;

describe("Create Ledger's opening line", () => {
  it("writes nothing without a chosen account (A)", () => {
    expect(openingSelection(accountsOf("PERSONAL"), "", "2500")).toBe(null);
  });

  it("writes nothing for an account another preset offered (B, C)", () => {
    expect(
      openingSelection(accountsOf("PORTFOLIO"), "Assets:Cash", "1000"),
    ).toBe(null);
    expect(openingSelection(accountsOf("BLANK"), "Assets:Cash", "1000")).toBe(
      null,
    );
  });

  it("writes the account the preset offers, with its amount", () => {
    expect(
      openingSelection(accountsOf("PERSONAL"), "Assets:Cash", "1000"),
    ).toEqual({ name: "Assets:Cash", amount: "1000" });
    expect(openingSelection(accountsOf("PERSONAL"), "Assets:Cash", "")).toBe(
      null,
    );
  });

  it("resets on a preset or start change, hides the amount, and shows it on Review", () => {
    const source = fs.readFileSync(
      path.join(__dirname, "..", "create-ledger-screen.tsx"),
      "utf8",
    );
    expect(source.includes("if (id !== presetId) resetOpening();")).toBe(true);
    expect(source.includes("if (kind !== startKind) resetOpening();")).toBe(
      true,
    );
    expect(source.includes("{openingAccountValue ? (")).toBe(true);
    expect(source.includes('t("createLedgerReviewOpening", {')).toBe(true);
  });
});
