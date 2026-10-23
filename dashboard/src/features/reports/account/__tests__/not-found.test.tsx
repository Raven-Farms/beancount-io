import {
  ApolloClient,
  ApolloLink,
  InMemoryCache,
  Observable,
} from "@apollo/client";
import {
  act,
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  createMemoryHistory,
  createRootRouteWithContext,
  createRoute,
  createRouter,
  HeadContent,
  Outlet,
  RouterProvider,
} from "@tanstack/react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { RouterContext } from "@/common/types/router-context";
import { createLocalization } from "@/i18n/init";
import { LocalizationProvider } from "@/i18n/provider";
import { Route as AccountRoute } from "@/routes/ledger.$ledgerOwner.$ledgerName.account.$accountName";

vi.unmock("@/common/hooks/use-translations");
vi.unmock("react-i18next");

afterEach(cleanup);

async function accountRouter(
  accountName: string,
  language: "en" | "de" = "en",
  providedClient?: ApolloClient,
) {
  const client =
    providedClient ??
    new ApolloClient({
      cache: new InMemoryCache(),
      link: new ApolloLink(
        () =>
          new Observable((observer) => {
            observer.next({
              data: { getLedgerAccounts: ["Assets:Cash", "Assets:Closed"] },
            });
            observer.complete();
          }),
      ),
    });
  const localization = createLocalization();
  await localization.changeLanguage(language);
  const root = createRootRouteWithContext<RouterContext>()({
    component: () => (
      <>
        <HeadContent />
        <main id="main-content">
          <Outlet />
        </main>
      </>
    ),
  });
  const ledger = createRoute({
    getParentRoute: () => root,
    path: "/ledger/$ledgerOwner/$ledgerName",
    component: Outlet,
  });
  const account = createRoute({
    getParentRoute: () => ledger,
    path: "/account/$accountName",
    loader: AccountRoute.options.loader,
    head: AccountRoute.options.head,
    validateSearch: AccountRoute.options.validateSearch,
    notFoundComponent: AccountRoute.options.notFoundComponent,
    component: () => <h1>Existing account report</h1>,
  });
  const accounts = createRoute({
    getParentRoute: () => ledger,
    path: "/accounts",
    component: () => <h1>Accounts list</h1>,
  });
  const router = createRouter({
    routeTree: root.addChildren([ledger.addChildren([account, accounts])]),
    context: { client, localization },
    history: createMemoryHistory({
      initialEntries: [
        `/ledger/alice/books/account/${encodeURIComponent(accountName)}`,
      ],
    }),
    defaultHashScrollIntoView: false,
    Wrap: ({ children }) => (
      <LocalizationProvider localization={localization}>
        {children}
      </LocalizationProvider>
    ),
  });
  await router.load();
  render(<RouterProvider router={router} />);
  return router;
}

describe("missing account route", () => {
  it("removes successful account metadata when same-route invalidation finds the account was removed", async () => {
    const requests: Array<{
      name: string;
      variables: Record<string, unknown>;
    }> = [];
    let release: (() => void) | undefined;
    const client = new ApolloClient({
      cache: new InMemoryCache(),
      link: new ApolloLink(
        (operation) =>
          new Observable((observer) => {
            requests.push({
              name: operation.operationName,
              variables: { ...operation.variables },
            });
            const respond = (accounts: string[]) => {
              observer.next({ data: { getLedgerAccounts: accounts } });
              observer.complete();
            };
            if (requests.length === 1)
              respond(["Assets:Cash", "Assets:Closed"]);
            else release = () => respond(["Assets:Closed"]);
          }),
      ),
    });
    let invalidation: Promise<void> | undefined;
    try {
      const router = await accountRouter("Assets:Cash", "en", client);
      await waitFor(() => expect(router.state.status).toBe("idle"));
      expect(
        screen.getByRole("heading", { name: "Existing account report" }),
      ).toBeVisible();
      expect(document.title).toBe("Assets:Cash - books");
      expect(
        document.head.querySelector('link[rel="canonical"]'),
      ).not.toBeNull();
      expect(
        client.cache.evict({
          id: "ROOT_QUERY",
          fieldName: "getLedgerAccounts",
          args: { ledgerId: "alice/books" },
        }),
      ).toBe(true);
      act(() => {
        invalidation = router.invalidate({ sync: true });
      });
      await waitFor(() => expect(release).toBeDefined());
      expect(router.state.isLoading).toBe(true);
      await act(async () => {
        release!();
        await invalidation;
      });
      expect(
        await screen.findByRole("heading", {
          name: "No account named Assets:Cash in this ledger.",
        }),
      ).toBeVisible();
      expect(router.state.statusCode).toBe(404);
      const match = router.state.matches.at(-1)!;
      // The router retains the previous successful data even after this lookup fails.
      expect(match.loaderData).toEqual({ accountExists: true });
      expect(match.status).toBe("notFound");
      expect(document.head.querySelector('link[rel="canonical"]')).toBeNull();
      expect(document.head.querySelector('link[rel="alternate"]')).toBeNull();
      expect(
        [...document.head.querySelectorAll("title")].map(
          (title) => title.textContent,
        ),
      ).toEqual(["Page Not Found — /ledger/alice/books/account/Assets%3ACash"]);
      expect(
        document.head.querySelector('meta[name="robots"]'),
      ).toHaveAttribute("content", "noindex, follow");
      expect(requests).toEqual([
        { name: "GetLedgerAccounts", variables: { ledgerId: "alice/books" } },
        { name: "GetLedgerAccounts", variables: { ledgerId: "alice/books" } },
      ]);
    } finally {
      await act(async () => {
        release?.();
        await invalidation;
      });
      client.stop();
    }
  });

  it.each([
    [
      "en",
      "No account named Assets:Missing<{2026}> in this ledger.",
      "Accounts",
    ],
    [
      "de",
      "In diesem Hauptbuch gibt es kein Konto namens Assets:Missing<{2026}>.",
      "Konten",
    ],
  ] as const)(
    "renders a localized %s not-found inside the ledger main with an Accounts recovery",
    async (language, message, accountsLabel) => {
      const user = userEvent.setup();
      const router = await accountRouter("Assets:Missing<{2026}>", language);
      await waitFor(() =>
        expect(
          screen.getByRole("heading", { level: 1, name: message }),
        ).toBeVisible(),
      );
      expect(router.state.statusCode).toBe(404);
      expect(screen.getAllByRole("main")).toHaveLength(1);
      expect(
        within(screen.getByRole("main")).getAllByRole("heading", { level: 1 }),
      ).toHaveLength(1);
      expect(
        document.head.querySelector('meta[name="robots"]'),
      ).toHaveAttribute("content", "noindex, follow");
      expect(document.head.querySelector('link[rel="canonical"]')).toBeNull();
      expect(document.head.querySelector('link[rel="alternate"]')).toBeNull();
      expect(
        screen.queryByRole("button", { name: /retry|try again/i }),
      ).not.toBeInTheDocument();
      const link = screen.getByRole("link", { name: accountsLabel });
      expect(link).toHaveAttribute("href", "/ledger/alice/books/accounts");
      await user.click(link);
      await waitFor(() =>
        expect(
          screen.getByRole("heading", { name: "Accounts list" }),
        ).toBeInTheDocument(),
      );
      expect(router.state.statusCode).toBe(200);
    },
  );

  it("validates client navigation from a real account to a missing account, Back, and a closed account", async () => {
    const router = await accountRouter("Assets:Cash");
    expect(router.state.statusCode).toBe(200);
    expect(
      screen.getByRole("heading", { name: "Existing account report" }),
    ).toBeInTheDocument();
    await act(async () => {
      await router.navigate({
        to: "/ledger/$ledgerOwner/$ledgerName/account/$accountName",
        params: {
          ledgerOwner: "alice",
          ledgerName: "books",
          accountName: "NotARoot:Foo",
        },
      });
    });
    await waitFor(() =>
      expect(
        screen.getByRole("heading", {
          name: "No account named NotARoot:Foo in this ledger.",
        }),
      ).toBeInTheDocument(),
    );
    expect(router.state.statusCode).toBe(404);
    expect(
      screen.queryByRole("heading", { name: "Existing account report" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Accounts" })).toHaveAttribute(
      "href",
      "/ledger/alice/books/accounts",
    );

    await act(async () => router.history.back());
    await waitFor(() => {
      expect(router.state.location.pathname).toBe(
        "/ledger/alice/books/account/Assets%3ACash",
      );
      expect(
        screen.getByRole("heading", { name: "Existing account report" }),
      ).toBeInTheDocument();
    });
    await act(async () => {
      await router.navigate({
        to: "/ledger/$ledgerOwner/$ledgerName/account/$accountName",
        params: {
          ledgerOwner: "alice",
          ledgerName: "books",
          accountName: "Assets:Closed",
        },
      });
    });
    expect(router.state.statusCode).toBe(200);
    expect(
      screen.getByRole("heading", { name: "Existing account report" }),
    ).toBeInTheDocument();
    expect(document.head.querySelector('meta[name="robots"]')).toBeNull();
  });
});
