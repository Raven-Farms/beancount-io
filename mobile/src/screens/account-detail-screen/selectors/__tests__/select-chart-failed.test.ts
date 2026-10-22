import fs from "fs";
import path from "path";
import { selectChartFailed } from "../select-chart-failed";

// w21/239: a failed pull to refresh replaced the loaded chart with a skeleton
// that read as loading forever, with no stale banner.
describe("selectChartFailed", () => {
  const loaded = { data: { getLedgerAccountReport: {} }, error: undefined };
  const offlineRefresh = { data: loaded.data, error: new Error("Network") };
  const firstLoadFailed = { data: undefined, error: new Error("Network") };
  const idle = { data: undefined, error: undefined };

  it("keeps a loaded chart when its refresh fails", () => {
    expect(
      selectChartFailed({
        unitsCurrency: undefined,
        report: offlineRefresh,
        unitsReport: idle,
      }),
    ).toBe(false);
    expect(
      selectChartFailed({
        unitsCurrency: "VTI",
        report: idle,
        unitsReport: offlineRefresh,
      }),
    ).toBe(false);
  });

  it("fails only a first load with nothing to draw", () => {
    expect(
      selectChartFailed({
        unitsCurrency: undefined,
        report: firstLoadFailed,
        unitsReport: idle,
      }),
    ).toBe(true);
    expect(
      selectChartFailed({
        unitsCurrency: "VTI",
        report: idle,
        unitsReport: firstLoadFailed,
      }),
    ).toBe(true);
  });

  it("judges the report the chart actually draws", () => {
    // A market report that failed does not fail a units chart, and back.
    expect(
      selectChartFailed({
        unitsCurrency: "VTI",
        report: firstLoadFailed,
        unitsReport: loaded,
      }),
    ).toBe(false);
    expect(
      selectChartFailed({
        unitsCurrency: undefined,
        report: loaded,
        unitsReport: firstLoadFailed,
      }),
    ).toBe(false);
  });
});

describe("the account detail chart", () => {
  const read = (...parts: string[]) =>
    fs
      .readFileSync(path.join(__dirname, "..", "..", ...parts), "utf8")
      .replace(/\s+/g, "");

  it("offers a retry on a first-load failure and shows the stale banner on a failed refresh", () => {
    const screen = read("account-detail-screen.tsx");
    expect(screen.includes("error={chartFailed}")).toBe(true);
    expect(screen.includes("onRetry={retryChart}")).toBe(true);
    expect(
      screen.includes(
        "{data:reportData,error:reportError},{data:unitsReportData,error:unitsReportError},",
      ),
    ).toBe(true);
    const card = fs
      .readFileSync(
        path.join(
          __dirname,
          "..",
          "..",
          "..",
          "..",
          "components",
          "balance-chart-card",
          "index.tsx",
        ),
        "utf8",
      )
      .replace(/\s+/g, "");
    // A failure is a failure card, not the skeleton.
    expect(card.includes("<CardLoadFailureonRetry={onRetry}/>")).toBe(true);
    expect(card.includes("if(loading||error)")).toBe(false);
  });
});

describe("the account detail chart's series", () => {
  it("is carried to today, for the money and the units chart", () => {
    const screen = fs
      .readFileSync(
        path.join(__dirname, "..", "..", "account-detail-screen.tsx"),
        "utf8",
      )
      .replace(/\s+/g, "");
    expect(
      screen.includes(
        "selectAccountUnitsSeries(unitsCurrency,unitsReportData,today)",
      ),
    ).toBe(true);
    expect(
      screen.includes(
        "currentBalance?{balance:currentBalance,today}:undefined,today,",
      ),
    ).toBe(true);
  });
});
