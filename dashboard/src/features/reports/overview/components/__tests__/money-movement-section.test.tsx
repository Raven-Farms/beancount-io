import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MoneyMovementSection } from "../money-movement-section";

const searchParams = vi.hoisted(() => ({ account: "", filter: "", time: "" }));
vi.mock("@/common/hooks/use-ledger-search-params", () => ({
  useLedgerSearchParams: () => ({ searchParams }),
}));
vi.mock("@/common/hooks/use-ledger", () => ({
  useLedgerNavigateToAccount: () => vi.fn(),
  useLedger: () => ({ ledgerData: { options: {} } }),
}));
vi.mock("@tanstack/react-router", () => ({
  Link: ({ children }: { children: React.ReactNode }) => <a>{children}</a>,
}));

const props = {
  income: [{ date: "2026-04-30", balance: { USD: -100 }, accountBalances: {} }],
  expenses: [
    { date: "2026-05-31", balance: { USD: 15 }, accountBalances: {} },
    { date: "2027-01-31", balance: { USD: 0 }, accountBalances: {} },
  ],
  primaryCurrency: "USD",
  ledgerOwner: "open_ledger",
  ledgerName: "stock-example",
};

beforeEach(() =>
  Object.assign(searchParams, { account: "", filter: "", time: "" }),
);

describe("public money-movement default", () => {
  it("shows the latest activity and preserves an explicitly selected empty month", async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <MoneyMovementSection {...props} preferActiveMonth />,
    );
    expect(screen.getAllByText("May 2026")).toHaveLength(3);
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getAllByText("January 2027")).toHaveLength(3);
    rerender(<MoneyMovementSection {...props} preferActiveMonth />);
    expect(screen.getAllByText("January 2027")).toHaveLength(3);
    await user.click(screen.getByRole("button", { name: "Previous" }));
    expect(screen.getAllByText("May 2026")).toHaveLength(3);
  });

  it("preserves the workspace default for writers and private ledgers", () => {
    render(<MoneyMovementSection {...props} />);
    expect(screen.getAllByText("January 2027")).toHaveLength(3);
  });

  it("falls back to the final supplied interval when every amount is zero", () => {
    render(
      <MoneyMovementSection
        {...props}
        income={[]}
        expenses={[
          { date: "2027-01-31", balance: { USD: 0 }, accountBalances: {} },
        ]}
        preferActiveMonth
      />,
    );
    expect(screen.getAllByText("January 2027")).toHaveLength(3);
    expect(
      screen.getAllByText("No money movement for this period."),
    ).toHaveLength(2);
  });
});

/** Month-end interval dates from `first` through `last` (YYYY-MM). */
function months(first: string, last: string) {
  const dates: string[] = [];
  let [year, month] = first.split("-").map(Number);
  for (;;) {
    dates.push(new Date(Date.UTC(year, month, 0)).toISOString().slice(0, 10));
    if (`${year}-${String(month).padStart(2, "0")}` === last) return dates;
    month += 1;
    if (month > 12) [year, month] = [year + 1, 1];
  }
}

/** The synthetic ledger: activity through August 2026, nothing after. */
function series(dates: string[], activeMonth?: string) {
  const point = (date: string, amount: number) => ({
    date,
    balance: date.startsWith(activeMonth ?? "none") ? { USD: amount } : {},
    accountBalances: {},
  });
  return {
    income: dates.map((date) => point(date, -4000)),
    expenses: dates.map((date) => point(date, 2095.6)),
  };
}

describe("filtered money-movement default on 2026-10-15", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 9, 15, 12));
  });
  afterEach(() => vi.useRealTimers());

  it.each(["2026", "year", "2026-07 - 2026-12"])(
    "time=%s opens on the latest active month, not a future one",
    (time) => {
      const window =
        time === "2026-07 - 2026-12"
          ? ["2026-07", "2026-12"]
          : ["2026-01", "2026-12"];
      Object.assign(searchParams, { time });
      render(
        <MoneyMovementSection
          {...props}
          {...series(months(window[0], window[1]), "2026-08")}
        />,
      );
      expect(screen.getAllByText("August 2026")).toHaveLength(3);
      expect(screen.queryByText("December 2026")).toBeNull();
    },
  );

  it.each([{ account: "Expenses:Fees" }, { filter: "payee:Broker" }])(
    "applies the same default to %j",
    (filter) => {
      Object.assign(searchParams, filter);
      render(
        <MoneyMovementSection
          {...props}
          {...series(months("2026-01", "2026-12"), "2026-08")}
        />,
      );
      expect(screen.getAllByText("August 2026")).toHaveLength(3);
    },
  );

  it("opens a selection with no activity on its last month that has begun", () => {
    Object.assign(searchParams, { time: "year" });
    render(
      <MoneyMovementSection
        {...props}
        {...series(months("2026-01", "2026-12"))}
      />,
    );
    expect(screen.getAllByText("October 2026")).toHaveLength(3);
    expect(
      screen.getAllByText("No money movement for this period."),
    ).toHaveLength(2);
  });

  it("keeps a wholly future selection's empty state", () => {
    Object.assign(searchParams, { time: "2030" });
    render(
      <MoneyMovementSection
        {...props}
        {...series(months("2030-01", "2030-12"))}
      />,
    );
    expect(screen.getAllByText("December 2030")).toHaveLength(3);
    expect(
      screen.getAllByText("No money movement for this period."),
    ).toHaveLength(2);
  });
});
