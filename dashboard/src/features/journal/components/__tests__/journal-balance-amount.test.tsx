import { cleanup, render, screen, within } from "@testing-library/react";
import {
  Outlet,
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { afterEach, describe, expect, it } from "vitest";
import { DirectiveType, type JournalBalance } from "@/common/types/journal";
import { JournalTable } from "../journal-table";

afterEach(cleanup);

const assertion: JournalBalance = {
  directive_type: DirectiveType.BALANCE,
  entry_hash: "synthetic-balance-assertion",
  date: "2026-08-29",
  account: "Assets:Cash",
  amount: { number: "49.75", currency: "USD" },
  tolerance: null,
  diff_amount: null,
};

async function renderRow(directive: JournalBalance, isAccountJournal: boolean) {
  const root = createRootRoute({ component: () => <Outlet /> });
  const journal = createRoute({
    getParentRoute: () => root,
    path: "/",
    component: () => (
      <JournalTable
        data={[{ directive, change: {}, balance: {} }]}
        isAccountJournal={isAccountJournal}
        accountName="Assets:Cash"
        showMetadata={false}
        showPostings={false}
        ledgerOwner="owner"
        ledgerName="ledger"
        onEntryClick={() => {}}
      />
    ),
  });
  const router = createRouter({
    routeTree: root.addChildren([journal]),
    history: createMemoryHistory({ initialEntries: ["/"] }),
    isServer: false,
  });
  await router.load();
  render(<RouterProvider router={router} />);
  const table = await screen.findByRole("table");
  return within(table).getAllByRole("row")[1];
}

describe("Balance rows show the asserted amount (w3/556)", () => {
  it.each([
    ["the journal", false],
    ["the account journal", true],
  ])("reads Assets:Cash … 49.75 USD in %s", async (_name, isAccountJournal) => {
    const row = await renderRow(assertion, isAccountJournal);

    expect(within(row).getByText("Assets:Cash")).toBeInTheDocument();
    const amount = within(row).getByText("49.75 USD");
    // Isolated so RTL layouts keep the number and currency in order.
    expect(amount.tagName).toBe("BDI");
    expect(amount).toHaveAttribute("dir", "ltr");
  });

  it("names the entry by its account and amount, not as a price", async () => {
    const row = await renderRow(assertion, false);

    expect(
      within(row).getByRole("button", {
        name: "Open entry 2026-08-29 Balance Assets:Cash 49.75 USD (row 1)",
      }),
    ).toBeInTheDocument();
  });

  it("shows an explicit tolerance with the amount", async () => {
    const row = await renderRow({ ...assertion, tolerance: "0.01" }, false);

    expect(within(row).getByText("49.75 ~ 0.01 USD")).toBeInTheDocument();
  });

  it("still renders the account when an older service omits the amount", async () => {
    const { amount: _omitted, ...legacy } = assertion;
    const row = await renderRow(legacy, false);

    expect(within(row).getByText("Assets:Cash")).toBeInTheDocument();
    expect(within(row).queryByText(/USD/)).not.toBeInTheDocument();
  });
});
