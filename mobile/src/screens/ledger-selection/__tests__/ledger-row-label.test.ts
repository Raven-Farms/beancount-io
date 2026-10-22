import fs from "fs";
import path from "path";
import { ledgerRowAccessibilityLabel } from "../ledger-row-label";
import { exampleCardAccessibilityLabel } from "../../examples/example-card-label";

// w21/243: a label on a pressable replaces its children, so VoiceOver read a
// ledger row by name only: never Private or Public, never the description.
describe("ledgerRowAccessibilityLabel", () => {
  it("reads the name, whether it is private, then the description", () => {
    expect(
      ledgerRowAccessibilityLabel({
        open: "Open qa/my-book",
        visibility: "Private",
        description: "Household budget",
      }),
    ).toBe("Open qa/my-book, Private, Household budget");
  });

  it("says Current for the open ledger and skips an empty description", () => {
    expect(
      ledgerRowAccessibilityLabel({
        open: "Open qa/my-book",
        visibility: "Public",
        description: "   ",
        current: "Current",
      }),
    ).toBe("Open qa/my-book, Public, Current");
    expect(
      ledgerRowAccessibilityLabel({
        open: "Open a/b",
        visibility: "Private",
        description: null,
      }),
    ).toBe("Open a/b, Private");
  });

  it("tells a private and a public ledger of one name apart", () => {
    const row = (visibility: string) =>
      ledgerRowAccessibilityLabel({
        open: "Open qa/book",
        visibility,
        description: undefined,
      });
    expect(row("Private") === row("Public")).toBe(false);
  });
});

describe("exampleCardAccessibilityLabel", () => {
  it("reads why an example cannot be opened", () => {
    expect(
      exampleCardAccessibilityLabel(
        "Open Nvidia",
        "This example is unavailable.",
      ),
    ).toBe("Open Nvidia, This example is unavailable.");
  });

  it("reads an available example's description, and a loading card's name alone", () => {
    expect(
      exampleCardAccessibilityLabel("Open Nvidia", "Stocks and options"),
    ).toBe("Open Nvidia, Stocks and options");
    expect(exampleCardAccessibilityLabel("Open Nvidia", null)).toBe(
      "Open Nvidia",
    );
  });
});

describe("the three ledger lists", () => {
  const read = (...parts: string[]) =>
    fs
      .readFileSync(path.join(__dirname, "..", "..", "..", ...parts), "utf8")
      .replace(/\s+/g, "");

  it("label their rows from what the rows show", () => {
    expect(
      read("screens", "ledger-selection", "index.tsx").includes(
        "accessibilityLabel={ledgerRowAccessibilityLabel({",
      ),
    ).toBe(true);
    expect(
      read("screens", "examples", "example-selector.tsx").includes(
        "accessibilityLabel={exampleCardAccessibilityLabel(",
      ),
    ).toBe(true);
    // The drawer's rows already read their status (w21/142); keep it so.
    expect(
      read("components", "ledger-drawer", "ledger-drawer.tsx").includes(
        "`${item.fullName},${item.statusLabel}`",
      ),
    ).toBe(true);
  });
});
