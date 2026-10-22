import {
  ApolloClient,
  ApolloLink,
  InMemoryCache,
  Observable,
} from "@apollo/client";
import { ApolloProvider } from "@apollo/client/react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  Outlet,
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { createInstance } from "i18next";
import { I18nextProvider } from "react-i18next";
import { afterEach, describe, expect, it, vi } from "vitest";
import { en } from "@/i18n/locales";
import { ledgerFilterSearchSchema } from "@/common/lib/ledger-search-params";
import LedgerHoldingsPage from "../index";
import { holdingsSearchSchema } from "../search";
import {
  holdingsStatementByAccount,
  holdingsStatementByCurrency,
} from "../holdings-statement";

vi.unmock("@/common/hooks/use-translations");
vi.unmock("react-i18next");

vi.mock("@/common/hooks/use-ledger", () => ({
  useLedger: () => ({ ledgerName: "My books" }),
}));
vi.mock("@/common/components/related-links", () => ({
  RelatedLinks: () => null,
}));

const TABLE = {
  __typename: "QueryShellResult",
  resultType: "table",
  text: null,
  table: {
    __typename: "QueryShellTable",
    types: [
      { __typename: "QueryShellType", name: "units" },
      { __typename: "QueryShellType", name: "book_value" },
    ],
    rows: [
      [{ ETH: "7.07495" }, { USD: "12000.00" }],
      [{ BTC: "0.5" }, { USD: "30000.00" }],
    ],
  },
};

type Read = {
  variables: Record<string, unknown>;
  settle: (ok: boolean) => void;
};

/**
 * QueryShell reads the test settles by hand, per statement. The first read of
 * each statement in `failFirst` fails; later reads wait in `held`.
 */
async function mountHoldings(view: string, failFirst: string[]) {
  const reads: Read[] = [];
  const held: Read[] = [];
  const seen = new Map<string, number>();
  const client = new ApolloClient({
    cache: new InMemoryCache(),
    link: new ApolloLink(
      (operation) =>
        new Observable((observer) => {
          const variables = operation.variables;
          const read: Read = {
            variables,
            settle: (ok) =>
              setTimeout(() => {
                if (!ok)
                  return observer.error(new TypeError("Failed to fetch"));
                observer.next({ data: { queryShell: TABLE } });
                observer.complete();
              }),
          };
          reads.push(read);
          const query = String(variables.query);
          const count = (seen.get(query) ?? 0) + 1;
          seen.set(query, count);
          if (count === 1) read.settle(!failFirst.includes(query));
          else held.push(read);
        }),
    ),
  });
  const i18n = createInstance();
  await i18n.init({
    lng: "en",
    fallbackLng: "en",
    resources: { en: { translation: en } },
    interpolation: { escapeValue: false, prefix: "{", suffix: "}" },
  });
  const rootRoute = createRootRoute({ component: () => <Outlet /> });
  const ledgerRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/ledger/$ledgerOwner/$ledgerName",
    validateSearch: (search) => ledgerFilterSearchSchema.parse(search),
    component: () => <Outlet />,
  });
  const holdingsRoute = createRoute({
    getParentRoute: () => ledgerRoute,
    path: "/holdings",
    validateSearch: (search) => holdingsSearchSchema.parse(search),
    component: LedgerHoldingsPage,
  });
  const router = createRouter({
    routeTree: rootRoute.addChildren([
      ledgerRoute.addChildren([holdingsRoute]),
    ]),
    history: createMemoryHistory({
      initialEntries: [`/ledger/alice/books/holdings?view=${view}`],
    }),
  });
  await router.load();
  render(
    <I18nextProvider i18n={i18n}>
      <ApolloProvider client={client}>
        <RouterProvider router={router} />
      </ApolloProvider>
    </I18nextProvider>,
  );
  return { reads, held, client };
}

const clients: ApolloClient[] = [];
afterEach(() => {
  cleanup();
  clients.splice(0).forEach((client) => client.stop());
});

/** A failed Holdings read retries its own grouping in place (w4/337). */
describe("Holdings read failure", () => {
  it("retries the selected grouping's read by keyboard until it lands", async () => {
    const user = userEvent.setup();
    const { reads, held, client } = await mountHoldings("by-currency", [
      holdingsStatementByCurrency,
    ]);
    clients.push(client);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/Connection problem/);
    expect(screen.queryByRole("table")).toBeNull();
    const retry = screen.getByRole("button", { name: "Try Again" });
    retry.focus();
    await user.keyboard("{Enter}");
    await waitFor(() => expect(held).toHaveLength(1));

    // Pending: the error view stays, busy, and a second Enter sends nothing.
    expect(retry).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent(/Connection problem/);
    await user.keyboard("{Enter}");
    expect(held).toHaveLength(1);

    held.shift()!.settle(false);
    await waitFor(() => expect(retry).toHaveFocus());
    expect(screen.getByRole("alert")).toHaveTextContent(/Connection problem/);

    await user.keyboard("{Enter}");
    await waitFor(() => expect(held).toHaveLength(1));
    held.shift()!.settle(true);
    const table = await screen.findByRole("table", {
      name: "Holdings by Currency",
    });
    expect(table.querySelectorAll("tbody tr")).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Export CSV" })).toBeEnabled();
    expect(screen.queryByRole("alert")).toBeNull();

    // Every attempt was the same grouping's read, with the same variables.
    expect(reads).toHaveLength(3);
    for (const read of reads) {
      expect(read.variables).toEqual(reads[0]!.variables);
      expect(read.variables.query).toBe(holdingsStatementByCurrency);
    }
  });

  it("keeps each grouping's own query, so another grouping loads beside a failed one", async () => {
    const user = userEvent.setup();
    const { reads, client } = await mountHoldings("by-currency", [
      holdingsStatementByCurrency,
    ]);
    clients.push(client);
    await screen.findByRole("button", { name: "Try Again" });

    await user.click(screen.getByRole("tab", { name: "Holdings by Account" }));
    expect(
      await screen.findByRole("table", { name: "Holdings by Account" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
    expect(reads.map((read) => read.variables.query)).toEqual([
      holdingsStatementByCurrency,
      holdingsStatementByAccount,
    ]);
  });
});
