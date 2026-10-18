import {
  ApolloClient,
  ApolloLink,
  InMemoryCache,
  Observable,
} from "@apollo/client";
import { ApolloProvider } from "@apollo/client/react";
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
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  RouterProvider,
  useParams,
} from "@tanstack/react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useLedgerSearchParams } from "@/common/hooks/use-ledger-search-params";
import { journalActionSearchSchema } from "@/common/lib/ledger-action-search";
import { ledgerFilterSearchSchema } from "@/common/lib/ledger-search-params";
import { LedgerSearchParamsProvider } from "@/common/providers/ledger-search-params-provider";
import { AccountJournalTable } from "@/features/reports/account";
import { accountJournalSearchSchema } from "@/features/reports/account/search";
import { createLocalization } from "@/i18n/init";
import { LocalizationProvider } from "@/i18n/provider";
import LedgerJournalPage from "../journal-page";

// The post-write error check (w3/640) has its own suite.
vi.mock("@/common/hooks/use-write-outcome", () => ({
  useWriteOutcome: () => ({ snapshot: () => null, report: async () => false }),
}));

vi.unmock("@/common/hooks/use-translations");
vi.unmock("react-i18next");
vi.mock("@/common/hooks/use-is-authenticated", () => ({
  useIsAuthenticated: () => false,
}));
vi.mock("@/common/providers/ledger-provider", () => ({
  useLedger: () => ({
    ledgerName: "Synthetic books",
    ledgerData: {
      options: { renderCommas: true },
      fava_options: {},
      permissions: { pull: true },
    },
  }),
}));

const clients: ApolloClient[] = [];
beforeEach(() => {
  vi.mocked(localStorage.getItem).mockReturnValue(null);
});
afterEach(() => {
  cleanup();
  clients.splice(0).forEach((client) => client.stop());
});

function AccountFixture() {
  const { ledgerOwner, ledgerName, accountName } = useParams({
    from: "/ledger/$ledgerOwner/$ledgerName/account/$accountName",
  });
  const { searchParams } = useLedgerSearchParams();
  return (
    <AccountJournalTable
      ledgerId={`${ledgerOwner}/${ledgerName}`}
      ledgerOwner={ledgerOwner}
      ledgerName={ledgerName}
      accountName={accountName}
      ledgerFilters={searchParams}
      conversion="at_cost"
    />
  );
}

function ScopeControls() {
  const { searchParams, setSearchParams } = useLedgerSearchParams();
  return (
    <button onClick={() => setSearchParams({ ...searchParams, time: "2025" })}>
      Change period
    </button>
  );
}

type Kind = "journal" | "account";
type Request = {
  query: { offset: number; limit: number; time?: string };
  resolve: (total?: number) => void;
  reject: () => void;
};

async function setup(kind: Kind, language: "en" | "de" = "en") {
  const requests: Request[] = [];
  const client = new ApolloClient({
    cache: new InMemoryCache(),
    link: new ApolloLink(
      (operation) =>
        new Observable((observer) => {
          const { query } = operation.variables;
          requests.push({
            query: { ...query },
            reject: () =>
              observer.error(new Error("Synthetic page request failed")),
            resolve: (total = query.limit * 7) => {
              const entries = Array.from(
                {
                  length: Math.max(
                    0,
                    Math.min(query.limit, total - query.offset),
                  ),
                },
                (_, index) => ({
                  directive_type: "Transaction",
                  date: "2026-10-15",
                  flag: "*",
                  payee: `row-${query.offset + index}`,
                  narration: "Synthetic pagination",
                  postings: [],
                  tags: [],
                  links: [],
                  meta: {},
                }),
              );
              observer.next({
                data:
                  operation.operationName === "GetLedgerJournal"
                    ? {
                        getLedgerJournal: {
                          __typename: "JournalResponse",
                          total,
                          is_empty: total === 0,
                          data: entries,
                        },
                      }
                    : {
                        getLedgerAccountJournal: {
                          __typename: "AccountJournalResponse",
                          total,
                          account: "Assets:Cash",
                          with_children: true,
                          items: entries.map((entry) => ({
                            __typename: "AccountJournalEntry",
                            entry,
                            change: { USD: "1" },
                            balance: { USD: "100" },
                          })),
                        },
                      },
              });
              observer.complete();
            },
          });
        }),
    ),
  });
  clients.push(client);
  const localization = createLocalization();
  await localization.changeLanguage(language);
  const root = createRootRoute({ component: () => <Outlet /> });
  const ledger = createRoute({
    getParentRoute: () => root,
    path: "/ledger/$ledgerOwner/$ledgerName",
    validateSearch: (search) => ledgerFilterSearchSchema.parse(search),
    component: () => (
      <LedgerSearchParamsProvider>
        <ScopeControls />
        <Outlet />
        <button>After journal</button>
      </LedgerSearchParamsProvider>
    ),
  });
  const journal = createRoute({
    getParentRoute: () => ledger,
    path: "/journal",
    validateSearch: (search) => journalActionSearchSchema.parse(search),
    component: LedgerJournalPage,
  });
  const account = createRoute({
    getParentRoute: () => ledger,
    path: "/account/$accountName",
    validateSearch: (search) => accountJournalSearchSchema.parse(search),
    component: AccountFixture,
  });
  const router = createRouter({
    routeTree: root.addChildren([ledger.addChildren([journal, account])]),
    history: createMemoryHistory({
      initialEntries: [
        `/ledger/alice/books/${kind === "journal" ? "journal" : "account/Assets%3ACash"}`,
      ],
    }),
  });
  await router.load();
  render(
    <LocalizationProvider localization={localization}>
      <ApolloProvider client={client}>
        <RouterProvider router={router} />
      </ApolloProvider>
    </LocalizationProvider>,
  );
  await waitFor(() => expect(requests).toHaveLength(1));
  await act(async () => requests[0].resolve());
  await screen.findByText("row-0");
  const t = localization.i18n.t.bind(localization.i18n);
  const pagination = () =>
    screen.getByRole("navigation", { name: t("common.paginationNav") });
  return {
    requests,
    router,
    t,
    pagination,
    user: userEvent.setup(),
    limit: kind === "journal" ? 60 : 20,
  };
}

describe("owning Journal and Account journal pagination focus", () => {
  it.each(
    (["journal", "account"] as const).flatMap((kind) =>
      (["en", "de"] as const).map((language) => [kind, language] as const),
    ),
  )(
    "retains %s controls through delayed and cached reads with localized %s range announcements",
    async (kind, language) => {
      const { pagination, user, t, requests, limit } = await setup(
        kind,
        language,
      );
      const status = screen.getByRole("status");
      const range = (first: number, last: number) =>
        language === "en"
          ? `Showing ${first}–${last} of ${limit * 7}`
          : `Ergebnisse ${first}–${last} von ${limit * 7}`;
      expect(status).toHaveTextContent(range(1, limit));
      const next = within(pagination()).getByRole("button", {
        name: t("common.goToNextPage"),
      });
      next.focus();
      await user.keyboard("{Enter}");
      await waitFor(() => expect(requests).toHaveLength(2));
      expect(requests[1].query.offset).toBe(limit);
      expect(next).toBeInTheDocument();
      expect(next).toHaveFocus();
      expect(next).toHaveAttribute("aria-disabled", "true");
      expect(next).not.toBeDisabled();
      expect(status).toBeEmptyDOMElement();
      expect(screen.queryByRole("table")).not.toBeInTheDocument();
      await user.keyboard("{Enter} ");
      expect(requests).toHaveLength(2);
      await act(async () => requests[1].resolve());
      await screen.findByText(`row-${limit}`);
      expect(next).toHaveFocus();
      expect(status).toHaveTextContent(range(limit + 1, limit * 2));

      const previous = within(pagination()).getByRole("button", {
        name: t("common.goToPreviousPage"),
      });
      previous.focus();
      await user.keyboard("{Enter}");
      await waitFor(() => expect(requests).toHaveLength(3));
      expect(requests[2].query.offset).toBe(0);
      expect(previous).toHaveFocus();
      expect(previous).not.toBeDisabled();
      expect(previous).toHaveAttribute("aria-disabled", "true");
      // Page one is cached, but its rows are withheld during revalidation.
      expect(screen.queryByRole("table")).not.toBeInTheDocument();
      expect(status).toBeEmptyDOMElement();
      await act(async () => requests[2].resolve());
      await screen.findByText("row-0");
      expect(previous).toBeDisabled();
      expect(
        within(pagination()).getByRole("button", { name: "1", exact: true }),
      ).toHaveFocus();
      expect(status).toHaveTextContent(range(1, limit));
    },
  );

  it.each(["journal", "account"] as const)(
    "keeps %s page-number identity as the range moves, and respects Tab and a new filter",
    async (kind) => {
      const { pagination, user, requests, limit, t, router } =
        await setup(kind);
      const page3 = within(pagination()).getByRole("button", {
        name: "3",
        exact: true,
      });
      page3.focus();
      await user.keyboard("{Enter}");
      await waitFor(() => expect(requests).toHaveLength(2));
      expect(page3).toBeInTheDocument();
      expect(page3).toHaveFocus();
      await act(async () => requests[1].resolve());
      expect(page3).toHaveAttribute("aria-current", "page");
      expect(page3).toHaveFocus();

      const page5 = within(pagination()).getByRole("button", {
        name: "5",
        exact: true,
      });
      page5.focus();
      await user.keyboard("{Enter}");
      await waitFor(() => expect(requests).toHaveLength(3));
      expect(page5).toBeInTheDocument();
      await user.tab();
      const tabbedTo = document.activeElement;
      expect(tabbedTo).not.toBe(document.body);
      expect(tabbedTo).not.toBe(page5);
      await act(async () => requests[2].resolve());
      expect(tabbedTo).toHaveFocus();
      expect(page5).toHaveAttribute("aria-current", "page");

      const next = within(pagination()).getByRole("button", {
        name: t("common.goToNextPage"),
      });
      next.focus();
      await user.keyboard("{Enter}");
      await waitFor(() => expect(requests).toHaveLength(4));
      const period = screen.getByRole("button", { name: "Change period" });
      await user.click(period);
      await waitFor(() => expect(requests).toHaveLength(5));
      expect(requests[4].query).toMatchObject({ offset: 0, time: "2025" });
      expect(screen.queryByRole("table")).not.toBeInTheDocument();
      expect(
        screen.queryByRole("navigation", { name: t("common.paginationNav") }),
      ).not.toBeInTheDocument();
      await act(async () => requests[3].resolve());
      expect(screen.queryByRole("table")).not.toBeInTheDocument();
      expect(period).toHaveFocus();
      await act(async () => requests[4].resolve());
      await screen.findByText("row-0");
      expect(period).toHaveFocus();
      expect(router.state.location.search).not.toHaveProperty("offset");
      expect(screen.getByRole("status")).toHaveTextContent(
        `Showing 1–${limit} of ${limit * 7}`,
      );
    },
  );

  it.each(["journal", "account"] as const)(
    "uses the %s result fallback when the collection becomes empty during paging",
    async (kind) => {
      const { pagination, user, requests, t, router } = await setup(kind);
      const fallback = screen.getByRole("table").closest('[tabindex="-1"]');
      expect(fallback).not.toBeNull();
      const next = within(pagination()).getByRole("button", {
        name: t("common.goToNextPage"),
      });
      next.focus();
      await user.keyboard("{Enter}");
      await waitFor(() => expect(requests).toHaveLength(2));
      await act(async () => requests[1].resolve(0));
      await waitFor(() => expect(fallback).toHaveFocus());
      await waitFor(() =>
        expect(router.state.location.search).not.toHaveProperty("offset"),
      );
      await waitFor(() => expect(requests).toHaveLength(3));
      await act(async () => requests[2].resolve(0));
      expect(fallback).toHaveFocus();
      expect(screen.queryByRole("table")).not.toBeInTheDocument();
      expect(
        screen.queryByRole("navigation", { name: t("common.paginationNav") }),
      ).not.toBeInTheDocument();
    },
  );

  it.each(["journal", "account"] as const)(
    "unlocks %s pagination after a failed Apollo page read",
    async (kind) => {
      const { pagination, user, requests, t, limit } = await setup(kind);
      const next = within(pagination()).getByRole("button", {
        name: t("common.goToNextPage"),
      });
      next.focus();
      await user.keyboard("{Enter}");
      await waitFor(() => expect(requests).toHaveLength(2));
      await act(async () => requests[1].reject());
      await waitFor(() =>
        expect(next).not.toHaveAttribute("aria-disabled", "true"),
      );
      expect(next).toHaveFocus();
      expect(screen.getByRole("status")).toBeEmptyDOMElement();
      const previous = within(pagination()).getByRole("button", {
        name: t("common.goToPreviousPage"),
      });
      previous.focus();
      await user.keyboard("{Enter}");
      await waitFor(() => expect(requests).toHaveLength(3));
      await act(async () => requests[2].resolve());
      await screen.findByText("row-0");
      next.focus();
      await user.keyboard("{Enter}");
      await waitFor(() => expect(requests).toHaveLength(4));
      expect(requests[3].query.offset).toBe(limit);
      await act(async () => requests[3].resolve());
      await screen.findByText(`row-${limit}`);
      expect(next).toHaveFocus();
    },
  );
});
