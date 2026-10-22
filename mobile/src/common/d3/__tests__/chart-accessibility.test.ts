import fs from "fs";
import path from "path";
import { en } from "../../../translations/en";
import { translationLocales } from "../../../translations/__tests__/locale-parity";
import {
  CHART_STEP_REST_MS,
  chartPointText,
  chartSummaryLabel,
  stepChartIndex,
  type ChartAccessibilitySeries,
} from "../chart-accessibility";

// w21/316: VoiceOver read the headline and the change row and skipped the
// curve, and a one-finger drag is a navigation gesture there, so no earlier
// month was reachable.
const dollars = (value: number, includePlus = false) =>
  `${value < 0 ? "-" : includePlus ? "+" : ""}$${Math.abs(value).toFixed(2)}`;
const translate = (key: string, params?: Record<string, unknown>) => {
  const template: string =
    (en as unknown as Record<string, string>)[key] ??
    (key === "Jan" ? "Jan" : key);
  return Object.entries(params ?? {}).reduce(
    (text, [name, value]) => text.split(`{{${name}}}`).join(String(value)),
    template,
  );
};
const series: ChartAccessibilitySeries = {
  labels: ["Jan", "Feb", "Mar"],
  periods: ["2026-01", "2026-02", "2026-03"],
  numbers: [1000, 1300, 1100],
  baseline: 900,
  format: dollars,
  translate,
};

describe("the chart's accessibility text", () => {
  it("summarises the range with its low and high", () => {
    expect(chartSummaryLabel("Net Worth", series)).toBe(
      "Net Worth, From Jan 2026, $1000.00, to Mar 2026, $1100.00. Low $1000.00, high $1300.00.",
    );
    expect(
      chartSummaryLabel(undefined, series)?.startsWith("From Jan 2026"),
    ).toBe(true);
  });

  it("has no summary without a curve to describe", () => {
    expect(chartSummaryLabel("x", { ...series, numbers: [5] })).toBe(null);
    expect(chartSummaryLabel("x", { ...series, numbers: [] })).toBe(null);
  });

  it("names the selected point with its change since the start", () => {
    expect(chartPointText(series, 1)).toBe(
      "Feb 2026, $1300.00, +$400.00 (+44.44%) since start",
    );
    // No percentage when the start is zero.
    expect(chartPointText({ ...series, baseline: 0 }, 0)).toBe(
      "Jan 2026, $1000.00, +$1000.00 since start",
    );
  });
});

describe("stepping through the months", () => {
  it("starts from the latest point and stays inside the series", () => {
    expect(stepChartIndex(null, -1, 12)).toBe(10);
    expect(stepChartIndex(null, 1, 12)).toBe(11);
    expect(stepChartIndex(0, -1, 12)).toBe(0);
    expect(stepChartIndex(11, 1, 12)).toBe(11);
    expect(stepChartIndex(5, 1, 12)).toBe(6);
    expect(stepChartIndex(5, -1, 12)).toBe(4);
  });

  it("rests after a few seconds", () => {
    expect(CHART_STEP_REST_MS >= 3000).toBe(true);
  });
});

describe("the chart plot", () => {
  const source = fs
    .readFileSync(
      path.join(__dirname, "..", "interactive-line-chart.tsx"),
      "utf8",
    )
    .replace(/\s+/g, "");

  it("is one adjustable element with a summary, a value, a hint and actions", () => {
    for (const piece of [
      "accessible={hasSeries}",
      'accessibilityRole={hasSeries?"adjustable":undefined}',
      "accessibilityLabel={plotLabel??undefined}",
      'accessibilityHint={hasSeries?t("chartAdjustHint"):undefined}',
      'accessibilityActions={hasSeries?[{name:"increment"},{name:"decrement"}]:undefined}',
      "onAccessibilityAction={onAccessibilityAction}",
    ]) {
      expect(source.includes(piece)).toBe(true);
    }
  });

  it("steps the same scrub index the header follows, and rests", () => {
    expect(source.includes("scrub.value=next;")).toBe(true);
    expect(source.includes("scrub.value=SCRUB_IDLE;")).toBe(true);
    expect(source.includes("setTimeout(")).toBe(true);
  });
});

describe("the chart's strings", () => {
  it("are in every shipped language", () => {
    for (const locale of translationLocales()) {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const catalog = require(`../../../translations/${locale}`)[locale];
      for (const key of ["chartSummary", "chartPointValue", "chartAdjustHint"])
        expect(typeof catalog[key]).toBe("string");
      expect(catalog.chartSummary.includes("{{startValue}}")).toBe(true);
      expect(catalog.chartPointValue.includes("{{change}}")).toBe(true);
    }
  });
});

// w21/317: the end dot and the cursor read the new series' coordinates at once
// while the line morphed, floating up to 48 px off the curve for ~450 ms.
describe("the end dot and cursor during a range change", () => {
  const source = fs
    .readFileSync(
      path.join(__dirname, "..", "interactive-line-chart.tsx"),
      "utf8",
    )
    .replace(/\s+/g, "");

  it("wait for the morph to land", () => {
    expect(
      source.includes("opacity:scrub.value===SCRUB_IDLE&&morph.value>=1?1:0"),
    ).toBe(true);
    // The cursor and its guide share the rule.
    expect(
      source.split("constactive=index!==SCRUB_IDLE&&morph.value>=1;").length -
        1,
    ).toBe(2);
  });
});
