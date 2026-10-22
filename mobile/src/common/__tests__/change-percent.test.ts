import fs from "fs";
import path from "path";
import { changePercent, formatChangePercent } from "../d3/change-percent";

const pct = (baseline: number, value: number) =>
  changePercent(baseline, value)?.toFixed(2) ?? null;

describe("changePercent", () => {
  it("measures a rise or fall between two positive values", () => {
    expect(pct(251635, 640480)).toBe("154.53");
    expect(pct(200, 150)).toBe("-25.00");
    expect(pct(100, 0)).toBe("-100.00");
  });

  it("measures a negative balance against its magnitude", () => {
    expect(pct(-1000, -500)).toBe("50.00");
    expect(pct(-500, -1000)).toBe("-100.00");
    expect(pct(-100, 0)).toBe("100.00");
  });

  it("has no percentage across a sign flip", () => {
    expect(pct(-76.38, 1346.68)).toBe(null);
    expect(pct(-1512.42, 5317.06)).toBe(null);
    expect(pct(250, -40)).toBe(null);
  });

  it("has no percentage from a zero start", () => {
    expect(pct(0, 5317.06)).toBe(null);
    expect(pct(0, 0)).toBe(null);
  });
});

describe("balance chart change row", () => {
  it("formats the change through changePercent, not a raw ratio", () => {
    const source = fs.readFileSync(
      path.join(__dirname, "..", "d3", "interactive-line-chart.tsx"),
      "utf8",
    );
    expect(source.includes("changePercent(baseline, shownValue)")).toBe(true);
    expect(source.includes("Math.abs(baseline)")).toBe(false);
  });
});

// w21/237: the percentage took its sign from the raw change and could print
// "-0.00%", beside an amount that already followed the rounded value.
describe("formatChangePercent", () => {
  const row = (baseline: number, value: number) => {
    const pct = changePercent(baseline, value);
    return pct === null ? null : formatChangePercent(pct);
  };

  it("reads a large balance's small drop as flat, not as -0.00%", () => {
    // 2,500,000 to 2,499,988: -$12.00 (0.00%).
    expect(row(2_500_000, 2_499_988)).toEqual({ text: "0.00%", flat: true });
  });

  it("reads a sub-cent move as flat, without a stray sign", () => {
    // 10234.567891 to 10234.565.
    expect(row(10234.567891, 10234.565)).toEqual({ text: "0.00%", flat: true });
    expect(row(10234.565, 10234.567891)).toEqual({ text: "0.00%", flat: true });
  });

  it("signs the rounded value", () => {
    expect(formatChangePercent(12.345)).toEqual({
      text: "+12.35%",
      flat: false,
    });
    expect(formatChangePercent(-3.2)).toEqual({ text: "-3.20%", flat: false });
    expect(formatChangePercent(0.004)).toEqual({ text: "0.00%", flat: true });
    expect(formatChangePercent(-0.004)).toEqual({ text: "0.00%", flat: true });
    expect(formatChangePercent(0.006)).toEqual({ text: "+0.01%", flat: false });
    expect(formatChangePercent(-0.006)).toEqual({
      text: "-0.01%",
      flat: false,
    });
  });
});

describe("the change row", () => {
  it("shows the rounded percentage and reads a flat change in the neutral colour", () => {
    const chart = fs
      .readFileSync(
        path.join(__dirname, "..", "d3", "interactive-line-chart.tsx"),
        "utf8",
      )
      .replace(/\s+/g, "");
    expect(chart.includes("formatChangePercent(changePct)")).toBe(true);
    expect(chart.includes("shownPct?.flat?neutralColor:color")).toBe(true);
    // No percentage is built from the raw change any more.
    expect(chart.includes('change>=0?"+":""')).toBe(false);
  });
});
