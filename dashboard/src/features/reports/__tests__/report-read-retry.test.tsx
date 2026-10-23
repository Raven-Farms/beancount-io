import {
  ApolloClient,
  ApolloLink,
  InMemoryCache,
  Observable,
  type Operation,
} from "@apollo/client";
import { ApolloProvider } from "@apollo/client/react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { FieldNode, OperationDefinitionNode } from "graphql";
import type { ComponentType, ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import AccountPage from "@/features/reports/account";
import BalanceSheetPage from "@/features/reports/balance-sheet";
import CashFlowPage from "@/features/reports/cash-flow";
import IncomeStatementPage from "@/features/reports/income-statement";
import TrialBalancePage from "@/features/reports/trial-balance";

vi.mock("@tanstack/react-router", () => ({
  useParams: () => ({
    ledgerOwner: "demo",
    ledgerName: "books",
    accountName: "Assets:Cash",
  }),
  useSearch: () => ({}),
  useNavigate: () => vi.fn(),
  ClientOnly: ({ children }: { children: ReactNode }) => <>{children}</>,
  Link: ({ children }: { children: ReactNode }) => <a href="#">{children}</a>,
}));
vi.mock("@/common/hooks/use-ledger", () => ({
  useLedger: () => ({
    ledgerName: "Demo Books",
    primaryCurrency: "USD",
    ledgerData: { options: { title: "" }, favaOptions: {} },
  }),
}));
vi.mock("@/common/hooks/use-ledger-search-params", () => ({
  useLedgerSearchParams: () => ({
    searchParams: { account: "", filter: "", time: "2016" },
  }),
}));
vi.mock("@/common/components/related-links", () => ({
  RelatedLinks: () => null,
}));
vi.mock("@/features/reports/balance-sheet/line-chart", () => ({
  LineChart: () => null,
}));
vi.mock("@/features/reports/income-statement/date-balance-chart", () => ({
  DateBalanceChart: () => null,
}));

/**
 * Each read answered empty: the reads these pages assume are present get
 * their smallest real shape, every other root field `null`.
 */
const EMPTY: Record<string, Record<string, unknown>> = {
  // The Account page needs its report before it shows the journal.
  GetLedgerAccountReport: {
    getLedgerAccountReport: {
      linechartData: [],
      intervalTotalsData: [],
      accountBalanceData: [],
    },
  },
  GetLedgerAccountJournal: {
    getLedgerAccountJournal: {
      with_children: false,
      total: 0,
      items: [],
      account: "Assets:Cash",
    },
  },
  GetLedgerCashFlow: {
    incomeIntervals: [],
    expenseIntervals: [],
    assetIntervals: [],
    liabilityIntervals: [],
    equityIntervals: [],
    getLedgerBalanceSheet: {
      assetsHierarchyData: {
        __typename: "SerializableTreeNode",
        account: "Assets",
        balance: {},
        balanceChildren: {},
        children: [],
        hasTxns: false,
        cost: null,
        costChildren: null,
      },
    },
    getLedgerAccountDirectives: [],
  },
};

function emptyAnswer(operation: Operation) {
  const known = EMPTY[operation.operationName ?? ""];
  if (known) return known;
  const definition = operation.query.definitions.find(
    (d): d is OperationDefinitionNode => d.kind === "OperationDefinition",
  )!;
  return Object.fromEntries(
    definition.selectionSet.selections.map((s) => {
      const field = s as FieldNode;
      return [(field.alias ?? field.name).value, null];
    }),
  );
}

/**
 * Fails the first `target` read, holds every later one until the test
 * settles it, and answers every other read empty.
 */
function readClient(target: string) {
  const reads: Record<string, unknown>[] = [];
  const held: ((ok: boolean) => void)[] = [];
  const client = new ApolloClient({
    cache: new InMemoryCache(),
    link: new ApolloLink(
      (operation) =>
        new Observable((observer) => {
          if (operation.operationName !== target) {
            observer.next({ data: emptyAnswer(operation) });
            observer.complete();
            return;
          }
          reads.push(operation.variables);
          const settle = (ok: boolean) => {
            if (!ok) return observer.error(new TypeError("Failed to fetch"));
            observer.next({ data: emptyAnswer(operation) });
            observer.complete();
          };
          if (reads.length === 1) settle(false);
          else held.push(settle);
        }),
    ),
  });
  return { client, reads, settle: (ok: boolean) => held.shift()?.(ok) };
}

/** Each failed observer offers Try Again on its own read (w4/m50). */
describe.each<[string, ComponentType, string]>([
  ["Trial Balance", TrialBalancePage, "GetLedgerTrialBalance"],
  ["Balance Sheet", BalanceSheetPage, "GetLedgerBalanceSheet"],
  ["Income Statement", IncomeStatementPage, "GetLedgerIncomeStatement"],
  ["Cash Flow", CashFlowPage, "GetLedgerCashFlow"],
  ["Account Journal", AccountPage, "GetLedgerAccountJournal"],
])("%s read failure", (_name, Page, target) => {
  it("retries its own read in place until it succeeds", async () => {
    const user = userEvent.setup();
    const { client, reads, settle } = readClient(target);
    render(
      <ApolloProvider client={client}>
        <Page />
      </ApolloProvider>,
    );

    const retry = await screen.findByRole("button", { name: "Try Again" });
    retry.focus();
    await user.keyboard("{Enter}");
    await waitFor(() => expect(reads).toHaveLength(2));
    // A pending retry stays where it was, busy, and starts nothing more.
    expect(retry).toBeDisabled();
    await user.keyboard("{Enter}");
    expect(reads).toHaveLength(2);

    // Another rejection is handled and offers the retry again.
    settle(false);
    await waitFor(() => expect(retry).toBeEnabled());
    await waitFor(() => expect(retry).toHaveFocus());

    await user.keyboard("{Enter}");
    await waitFor(() => expect(reads).toHaveLength(3));
    settle(true);
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Try Again" })).toBeNull(),
    );
    // Every retry asked for the same requested scope.
    expect(reads[1]).toEqual(reads[0]);
    expect(reads[2]).toEqual(reads[0]);
  });
});
