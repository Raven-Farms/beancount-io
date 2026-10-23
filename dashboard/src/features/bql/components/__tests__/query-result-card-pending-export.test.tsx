import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { QueryShellQuery } from "@/graphql/definitions";
import { QueryResultCard } from "../query-result-card";

const { exportCsv } = vi.hoisted(() => ({ exportCsv: vi.fn() }));
vi.mock("../../lib/export-utils", () => ({
  exportQueryResultAsCSV: (...args: unknown[]) => exportCsv(...args),
}));
vi.mock("@/common/hooks/use-translations", () => ({
  useTranslations: () => ({ t: (key: string) => key }),
}));

/**
 * The real card and its real CSV control: while a query runs again its old
 * table is hidden, so it is not offered for download (w4/297).
 */
type Result = NonNullable<QueryShellQuery["queryShell"]>;
const QUERY = "select account, number, currency limit 2";
const result = (rows: string[][]): Result =>
  ({
    __typename: "QueryShellResult",
    resultType: "table",
    table: {
      __typename: "QueryResultTable",
      types: [
        { name: "account", dtype: "str" },
        { name: "number", dtype: "Decimal" },
        { name: "currency", dtype: "str" },
      ],
      rows,
    },
    text: null,
    chart: null,
  }) as unknown as Result;
const PREVIOUS = [
  ["Assets:US:BofA:Checking", "3490.52", "USD"],
  ["Equity:Opening-Balances", "-3490.52", "USD"],
];
const NEXT = [["Assets:US:BofA:Checking", "3500.00", "USD"]];

function card(props: { result: Result | null; loading: boolean }) {
  return (
    <QueryResultCard
      query={QUERY}
      onExecute={vi.fn()}
      onDelete={vi.fn()}
      isInitiallyOpen
      {...props}
    />
  );
}
const download = () =>
  screen.queryByRole("button", { name: "bql.downloadCSV" });

describe("BQL card export while its query runs again", () => {
  it("withholds the previous table, then exports the new one", () => {
    const view = render(card({ result: result(PREVIOUS), loading: false }));
    expect(download()).toBeEnabled();

    view.rerender(card({ result: result(PREVIOUS), loading: true }));
    expect(download()).toBeNull();

    view.rerender(card({ result: result(NEXT), loading: false }));
    fireEvent.click(download()!);
    expect(exportCsv).toHaveBeenCalledTimes(1);
    expect(exportCsv.mock.calls[0][0].rows).toEqual(NEXT);
  });

  it("still exports a settled zero-row result", () => {
    render(card({ result: result([]), loading: false }));
    expect(download()).toBeInTheDocument();
  });
});
