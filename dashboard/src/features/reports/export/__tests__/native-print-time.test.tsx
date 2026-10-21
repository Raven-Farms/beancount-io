import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { StatementExportMenu } from "../statement-export-menu";
import type { StatementExportDocument } from "../model";

vi.mock("@/common/analytics/events", () => ({ track: vi.fn() }));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock("@/common/hooks/use-translations", () => ({
  useTranslations: () => ({
    t: (key: string, params?: Record<string, string>) =>
      params?.generatedAt ? `${key} ${params.generatedAt}` : key,
    i18n: { language: "en-US", dir: () => "ltr" },
  }),
}));

/** The browser captures the page as soon as beforeprint returns (w4/290). */
const document: StatementExportDocument = {
  kind: "balance_sheet",
  title: "Balance Sheet",
  context: {
    reportingEntity: "QA",
    reportingEntitySource: "ledger_title",
    ledgerName: "QA",
    primaryCurrency: "USD",
    conversion: "units",
    interval: "monthly",
    filters: { time: "", account: "", filter: "" },
    reportingPeriod: {
      startDate: null,
      endDate: null,
      asOfDate: "2026-10-20",
      isExplicit: false,
      selection: "",
    },
    generatedAt: "2026-10-20T17:00:00.000Z",
  },
  sections: [
    {
      key: "assets",
      label: "Assets",
      rows: [
        {
          accountPath: "Assets",
          label: "Assets",
          depth: 0,
          rowKind: "total",
          amounts: [{ unit: "USD", rawAmount: "1", displayAmount: "1" }],
        },
      ],
    },
  ],
};

const footer = () => screen.getByTestId("printable-statement").textContent;
/** Dispatch the way the browser does: no act() flush before capture. */
function nativePrint() {
  const previous = globalThis.IS_REACT_ACT_ENVIRONMENT;
  globalThis.IS_REACT_ACT_ENVIRONMENT = false;
  try {
    window.dispatchEvent(new Event("beforeprint"));
  } finally {
    globalThis.IS_REACT_ACT_ENVIRONMENT = previous;
  }
  return footer();
}

describe("native browser print generation time", () => {
  const originalTz = process.env.TZ;
  beforeEach(() => {
    process.env.TZ = "America/Los_Angeles";
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-10-20T17:00:00.000Z"));
  });
  afterEach(() => {
    vi.useRealTimers();
    process.env.TZ = originalTz;
  });

  it("stamps the first and every later print with the time of that print", () => {
    render(<StatementExportMenu document={document} />);

    vi.setSystemTime(new Date("2026-10-20T17:30:00.000Z"));
    expect(nativePrint()).toContain("10:30");

    vi.setSystemTime(new Date("2026-10-21T17:30:00.000Z"));
    const second = nativePrint();
    expect(second).toContain("Oct 21, 2026");
    // The report's own as-of date is not redated.
    expect(second).toContain("October 20, 2026");
  });

  it("keeps later report props and leaves the portal with pending data", async () => {
    const view = render(<StatementExportMenu document={document} />);
    vi.setSystemTime(new Date("2026-10-20T17:30:00.000Z"));
    nativePrint();

    await act(async () => {
      view.rerender(
        <StatementExportMenu
          document={{
            ...document,
            context: {
              ...document.context,
              reportingPeriod: {
                ...document.context.reportingPeriod,
                asOfDate: "2016-12-31",
              },
            },
          }}
        />,
      );
    });
    expect(footer()).toContain("December 31, 2016");

    await act(async () => {
      view.rerender(<StatementExportMenu document={document} ready={false} />);
    });
    expect(screen.queryByTestId("printable-statement")).toBeNull();
  });
});
