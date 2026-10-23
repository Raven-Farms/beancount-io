import fs from "fs";
import path from "path";

// w21/611: See all on Home's Spending card opened Reports on its own 6M, whose
// totals matched neither the card's This month nor Last month. Source checks
// (the screens need the native runtime).
const read = (...parts: string[]) =>
  fs
    .readFileSync(path.join(__dirname, "..", ...parts), "utf8")
    .replace(/\s+/g, "");

describe("Spending's See all", () => {
  it("asks Reports for the month the card shows, before switching tab", () => {
    const card = read("..", "home-screen", "components", "spending-card.tsx");
    expect(
      card.includes('constopenReports=()=>{requestedReportsRange("1M");'),
    ).toBe(true);
  });

  it("applies the request once and clears it", () => {
    const screen = read("reports-screen.tsx");
    expect(
      screen.includes(
        "if(requestedRange===null)return;setTimeRange(requestedRange);requestedReportsRange(null);",
      ),
    ).toBe(true);
  });
});
