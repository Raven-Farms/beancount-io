import fs from "fs";
import path from "path";
import { scaleLinear } from "d3-scale";
import { barChartValueDomain } from "../bar-chart-domain";
import { formatShortMoneyWithCurrency } from "../../number-utils";

/**
 * The spending bar chart's value domain. This file used to re-declare the
 * chart's `Math.max`/`Math.min` inline and test d3 against its own copy, so a
 * change to the chart could not fail it; the domain now lives in a module the
 * chart uses and this file imports.
 */
describe("barChartValueDomain", () => {
  it("runs from zero to the largest month when spending is positive", () => {
    expect(barChartValueDomain([10, 25, 15, 30, 20])).toEqual([0, 30]);
  });

  it("keeps zero and reaches below it for negative months", () => {
    expect(barChartValueDomain([100, -50, 75])).toEqual([-50, 100]);
    expect(barChartValueDomain([-10, -25])).toEqual([-25, 0]);
  });

  it("never collapses for an empty or all-zero series", () => {
    expect(barChartValueDomain([])).toEqual([0, 1]);
    expect(barChartValueDomain([0, 0])).toEqual([0, 1]);
  });

  it("is the domain the chart's y scale uses", () => {
    const source = fs.readFileSync(
      path.join(__dirname, "..", "bar-chart-d3.tsx"),
      "utf8",
    );
    expect(source.includes(".domain(barChartValueDomain(numbers))")).toBe(true);
  });

  // w21/236: a floor of 1 on every series drew a BTC ledger's spending as
  // slivers on a 0 to 1 axis.
  it("takes the real extent of a small-unit series", () => {
    expect(barChartValueDomain([0.042, 0.031])).toEqual([0, 0.042]);
    const scale = scaleLinear()
      .domain(barChartValueDomain([0.042, 0.031]))
      .range([170, 0])
      .nice();
    expect(scale.domain()).toEqual([0, 0.045]);
    // The tallest bar fills most of the axis instead of 7 px of 170.
    expect(170 - scale(0.042) > 140).toBe(true);
    const ticks = scale
      .ticks(5)
      .map((tick) => formatShortMoneyWithCurrency(tick, "BTC"));
    expect(new Set(ticks).size).toBe(ticks.length);
    expect(ticks).toEqual([
      "0 BTC",
      "0.01 BTC",
      "0.02 BTC",
      "0.03 BTC",
      "0.04 BTC",
    ]);
  });

  it("leaves a USD series as it was", () => {
    expect(barChartValueDomain([420, 310])).toEqual([0, 420]);
  });
});

// w21/456: the Budget chart kept its own floor of 1, so a BTC budget's bars were
// slivers on a 0 to 1 axis.
describe("the Budget chart's value domain", () => {
  it("takes the real extent of fractional actuals and budgets", () => {
    expect(barChartValueDomain([0.0021, 0.0042, 0.0035, 0.003, 0.003])).toEqual(
      [0, 0.0042],
    );
  });

  it("leaves a dollar budget's axis as it was", () => {
    expect(barChartValueDomain([120, 340, 90, 300, 300])).toEqual([0, 340]);
    expect(barChartValueDomain([0, 0])).toEqual([0, 1]);
  });

  it("is what the chart draws with", () => {
    const source = require("fs")
      .readFileSync(
        require("path").join(__dirname, "..", "budget-bar-chart-d3.tsx"),
        "utf8",
      )
      .replace(/\s+/g, "") as string;
    expect(
      source.includes(
        "const[yMin,yMax]=barChartValueDomain([...actuals,...budgets]);",
      ),
    ).toBe(true);
    expect(source.includes("Math.max(1,")).toBe(false);
  });
});
