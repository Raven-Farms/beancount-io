import { axisLabelWidth } from "../axis-label-width";
import { formatShortMoneyWithCurrency } from "../../number-utils";

describe("report axis currency labels", () => {
  it("keeps ordinary USD ticks at their existing width", () => {
    const labels = [-200, 0, 200].map((tick) =>
      formatShortMoneyWithCurrency(tick, "USD"),
    );
    expect(axisLabelWidth(labels, 12, 50)).toBe(50);
  });
  it("reserves space for MiniMax's negative MUSD ticks instead of clipping their sign and amount", () => {
    const labels = [-200, 0, 200].map((tick) =>
      formatShortMoneyWithCurrency(tick, "MUSD"),
    );
    expect(labels[0]).toBe("-200 MUSD");
    expect(axisLabelWidth(labels, 12, 50) >= 80).toBe(true);
  });
});

// w21/360: the Budget chart kept the fixed 50 px axis, so the German "2,5 Tsd. $"
// lost its leading digits and 2,500 and 1,500 both read "5 Tsd. $".
describe("budget chart axis (w21/360)", () => {
  it("grows past the default for languages with long compact labels", () => {
    const ticks = [0, 500, 1000, 1500, 2000, 2500, 3000];
    const width = (locale: string, currency = "USD") =>
      axisLabelWidth(
        ticks.map((tick) =>
          formatShortMoneyWithCurrency(tick, currency, locale),
        ),
        12,
        50,
      );
    expect(width("en")).toBe(50);
    expect(width("de") > 50).toBe(true);
    expect(width("ru") > 50).toBe(true);
    // Fractional commodity ticks need the room too.
    expect(width("en", "QABTC") > 50).toBe(true);
  });

  it("the Budget chart measures its ticks and sizes the plot by that width", () => {
    const fs = require("fs");
    const path = require("path");
    const src = fs
      .readFileSync(path.join(__dirname, "../budget-bar-chart-d3.tsx"), "utf8")
      .replace(/\s+/g, "");
    expect(
      src.includes(
        "constaxisWidth=axisLabelWidth(yTicks.map((tick)=>formatShortMoneyWithCurrency(tick,currency,locale)),AXIS_FONT_SIZE,LEFT_PADDING,);",
      ),
    ).toBe(true);
    expect(
      src.includes(
        "budgetColumnWidth(containerWidth,axisWidth,labels.length,MIN_COLUMN_WIDTH,)",
      ),
    ).toBe(true);
    expect(src.includes("axisWidth={axisWidth}")).toBe(true);
  });
});
