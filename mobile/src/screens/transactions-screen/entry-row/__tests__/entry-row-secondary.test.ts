import fs from "fs";
import path from "path";
import { entryRowSecondaryText, entryRowTitle } from "../entry-row-secondary";

describe("entryRowSecondaryText", () => {
  it("shows the narration under a payee that says something else", () => {
    expect(
      entryRowSecondaryText({
        payee: "Q2 2026 Expenses",
        narration: "Other cost of revenue",
      }),
    ).toBe("Other cost of revenue");
  });

  it("adds no line when the payee is the only text", () => {
    expect(entryRowSecondaryText({ payee: "Anthropic", narration: "" })).toBe(
      null,
    );
    expect(entryRowSecondaryText({ payee: "Anthropic" })).toBe(null);
  });

  it("adds no line when the narration is already the name", () => {
    expect(
      entryRowSecondaryText({ payee: null, narration: "Padding inserted" }),
    ).toBe(null);
  });

  it("adds no line when payee and narration match", () => {
    expect(
      entryRowSecondaryText({
        payee: "Cafe Medager",
        narration: " Cafe Medager ",
      }),
    ).toBe(null);
  });
});

describe("EntryRow secondary line wiring", () => {
  it("renders the narration line from the helper", () => {
    const source = fs.readFileSync(
      path.join(__dirname, "..", "index.tsx"),
      "utf8",
    );
    expect(source.includes("entryRowSecondaryText(entry)")).toBe(true);
    expect(source.includes("{secondary}")).toBe(true);
  });
});

// w21/568: `2026-10-15 * " " "Coffee"` showed a row with no text at all.
describe("entryRowTitle", () => {
  it("prefers the payee, then the narration", () => {
    expect(entryRowTitle({ payee: "Blue Bottle", narration: "latte" })).toBe(
      "Blue Bottle",
    );
    expect(entryRowTitle({ payee: null, narration: "latte" })).toBe("latte");
  });

  it("skips a payee that is only spaces", () => {
    expect(entryRowTitle({ payee: " ", narration: "qa-20261020 Coffee" })).toBe(
      "qa-20261020 Coffee",
    );
    expect(entryRowTitle({ payee: "  \t", narration: " Coffee " })).toBe(
      "Coffee",
    );
  });

  it("is nothing when both are blank, for the caller's untitled label", () => {
    expect(entryRowTitle({ payee: " ", narration: "  " })).toBe(undefined);
    expect(entryRowTitle({})).toBe(undefined);
  });

  it("is what the row uses for its name and its brand", () => {
    const row = fs
      .readFileSync(path.join(__dirname, "..", "index.tsx"), "utf8")
      .replace(/\s+/g, "");
    expect(row.includes("constname=entryRowTitle(entry)??untitledLabel;")).toBe(
      true,
    );
    expect(row.includes("?entryRowTitle(entry):undefined")).toBe(true);
  });
});
