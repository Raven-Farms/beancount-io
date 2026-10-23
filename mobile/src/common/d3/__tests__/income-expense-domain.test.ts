import fs from "fs";
import path from "path";
import { scaleLinear } from "d3-scale";
import { barChartValueDomain } from "../bar-chart-domain";

// A refund month nets expenses negative; the Income vs Expenses chart drew
// that bar below the plot floor, through the month label, because only the
// net line could lower the domain (w21/022).
describe("Income vs Expenses y-domain", () => {
  const FLOOR = 190;
  const TOP = 10;
  const scaleFor = (income: number[], expense: number[], net: number[]) =>
    scaleLinear()
      .domain(barChartValueDomain([...income, ...expense, ...net]))
      .range([FLOOR, TOP])
      .nice();

  it("keeps a negative expense bar inside the plot", () => {
    const y = scaleFor([0], [-80], [80]);
    expect(y(-80) <= FLOOR && y(-80) >= TOP).toBe(true);
    // A negative tick to read the bar against (d3 picks -50 here).
    expect(y.ticks(5)[0]! < 0).toBe(true);
  });

  it("leaves an ordinary month's floor at zero", () => {
    const y = scaleFor([500], [300], [200]);
    expect(y.domain()[0]).toBe(0);
  });

  it("is what the chart builds its scale from", () => {
    const source = fs.readFileSync(
      path.join(__dirname, "..", "income-expense-bar-chart.tsx"),
      "utf8",
    );
    expect(
      source.includes(
        ".domain(barChartValueDomain([...income, ...expense, ...net]))",
      ),
    ).toBe(true);
  });
});
