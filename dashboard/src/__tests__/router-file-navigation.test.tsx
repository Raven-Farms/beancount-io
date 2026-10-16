import {
  ApolloClient,
  ApolloLink,
  InMemoryCache,
  Observable,
} from "@apollo/client";
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { getRouter } from "@/router";

vi.unmock("@/common/hooks/use-translations");
vi.unmock("react-i18next");

const boundary = vi.hoisted(() => ({ getClient: vi.fn() }));
vi.mock("@/common/apollo/client", () => ({ getClient: boundary.getClient }));

// Keep the application's router factory/providers and actual Files page/links.
// Only the route inventory and the destination's heavy PDF viewer are bounded.
vi.mock("@/routeTree.gen", async () => {
  const {
    createRootRouteWithContext,
    createRoute,
    Link,
    Outlet,
    useLocation,
    useParams,
  } = await import("@tanstack/react-router");
  const { useQuery } = await import("@apollo/client/react");
  const { GetLedgerFileDocument } = await import("@/graphql/definitions");
  const { LedgerProvider } = await import("@/common/providers/ledger-provider");
  const { default: LedgerDirectoryPage } =
    await import("@/features/ledger-editor/directory-browse");
  const ledgerData = {
    __typename: "Ledger" as const,
    id: "synthetic/books",
    name: "books",
    fullName: "synthetic/books",
    description: null,
    httpUrl: "https://example.com/synthetic/books.git",
    sshUrl: "git@example.com:synthetic/books.git",
    private: false,
    empty: false,
    size: 100,
    createdAt: "2026-01-01T00:00:00Z",
    updatedAt: "2026-01-01T00:00:00Z",
    isStarred: false,
    permissions: {
      __typename: "Permission" as const,
      admin: false,
      pull: true,
      push: false,
    },
    options: {
      __typename: "LedgerOptions" as const,
      title: "Synthetic files",
      nameAssets: "Assets",
      nameEquity: "Equity",
      nameExpenses: "Expenses",
      nameIncome: "Income",
      nameLiabilities: "Liabilities",
      accountCurrentConversions: "Equity:Conversions:Current",
      accountCurrentEarnings: "Equity:Earnings:Current",
      renderCommas: true,
      operatingCurrency: ["USD"],
    },
    favaOptions: {
      __typename: "FavaOptions" as const,
      accountJournalIncludeChildren: true,
      autoReload: false,
      collapsePattern: [],
      conversionCurrencies: [],
      currencyColumn: 1,
      defaultPage: "income_statement",
      indent: 2,
      invertIncomeLiabilitiesEquity: true,
      language: null,
      locale: null,
      showAccountsWithZeroBalance: true,
      showAccountsWithZeroTransactions: true,
      showClosedAccounts: false,
      sidebarShowQueries: 5,
      unrealized: "Unrealized",
      upcomingEvents: 7,
      uptodateIndicatorGreyLookbackDays: 7,
      useExternalEditor: false,
      fiscalYearEnd: {
        __typename: "FiscalYearEnd" as const,
        month: 12,
        day: 31,
      },
    },
    bcioOptions: {
      __typename: "BcioOptions" as const,
      defaultFile: "main.bean",
      transactionFile: null,
      accountFile: null,
      priceFile: null,
      balanceFile: null,
      noteFile: null,
      padFile: null,
    },
  };
  const root = createRootRouteWithContext<
    import("@/common/types/router-context").RouterContext
  >()({
    component: () => (
      <LedgerProvider
        ledgerOwner="synthetic"
        ledgerName="books"
        ledgerData={ledgerData}
      >
        <Outlet />
      </LedgerProvider>
    ),
  });
  const directory = createRoute({
    getParentRoute: () => root,
    path: "/ledger/$ledgerOwner/$ledgerName/files/tree/$branch/$",
    component: LedgerDirectoryPage,
  });
  const blob = createRoute({
    getParentRoute: () => root,
    path: "/ledger/$ledgerOwner/$ledgerName/files/blob/$branch/$",
    component: function SyntheticFileBody() {
      const params = useParams({ strict: false });
      const location = useLocation();
      const { data } = useQuery(GetLedgerFileDocument, {
        variables: {
          ledgerId: `${params.ledgerOwner}/${params.ledgerName}`,
          path: params._splat ?? "",
        },
      });
      return (
        <main>
          <h1>{params._splat}</h1>
          <pre aria-label="Synthetic file body">
            {data?.getLedgerFile?.content
              ? atob(data.getLedgerFile.content)
              : ""}
          </pre>
          <output aria-label="File query and fragment">
            {JSON.stringify({ search: location.search, hash: location.hash })}
          </output>
          <Link
            to="/ledger/$ledgerOwner/$ledgerName/files/blob/$branch/$"
            params={{
              ledgerOwner: "synthetic",
              ledgerName: "books",
              branch: "main",
              _splat: params._splat ?? "",
            }}
            search={{ time: "2026", filter: 'document:"{2026}.pdf"' }}
            hash="diff-file-docs%2F%7B2026%7D.pdf"
          >
            Open scoped file reference
          </Link>
        </main>
      );
    },
  });
  return { routeTree: root.addChildren([directory, blob]) };
});

let client: ApolloClient | undefined;
afterEach(() => {
  cleanup();
  client?.stop();
  vi.unstubAllEnvs();
});

describe("application router Files navigation", () => {
  it("opens a brace-named file from the actual directory Link and preserves an explicit query/fragment reference", async () => {
    vi.stubEnv("PROD", true);
    const requests: Array<{
      name: string;
      variables: Record<string, unknown>;
    }> = [];
    const file = {
      __typename: "LedgerFileContent",
      name: "{2026}.pdf",
      path: "docs/{2026}.pdf",
      sha: "synthetic-file-sha",
      size: 47,
      type: "file",
      encoding: "base64",
      content: btoa("Synthetic PDF body for the {2026} receipt."),
      lastCommitSha: null,
      lastAuthorDate: null,
      lastCommitterDate: null,
    };
    client = new ApolloClient({
      cache: new InMemoryCache(),
      link: new ApolloLink(
        (operation) =>
          new Observable((observer) => {
            requests.push({
              name: operation.operationName,
              variables: { ...operation.variables },
            });
            const data =
              operation.operationName === "GetLedgerDirContent"
                ? { getLedgerDirContent: [file] }
                : operation.operationName === "GetLedgerFile"
                  ? { getLedgerFile: file }
                  : undefined;
            if (!data)
              observer.error(
                new Error(`Unexpected operation ${operation.operationName}`),
              );
            else {
              observer.next({ data });
              observer.complete();
            }
          }),
      ),
    });
    boundary.getClient.mockReturnValue(client);
    const router = getRouter();
    const history = createMemoryHistory({
      initialEntries: ["/ledger/synthetic/books/files/tree/main/docs"],
    });
    router.update({ history, isServer: false });
    await router.load();
    render(<RouterProvider router={router} />);
    const user = userEvent.setup();
    const fileLink = await screen.findByRole("link", { name: /\{2026\}\.pdf/ });
    expect(
      new URL(fileLink.getAttribute("href")!, window.location.origin).pathname,
    ).toBe("/ledger/synthetic/books/files/blob/main/docs/%7B2026%7D.pdf");
    await user.click(fileLink);
    expect(
      await screen.findByRole("heading", { name: "docs/{2026}.pdf" }),
    ).toBeVisible();
    expect(
      await screen.findByLabelText("Synthetic file body"),
    ).toHaveTextContent("Synthetic PDF body for the {2026} receipt.");
    expect(requests).toEqual([
      {
        name: "GetLedgerDirContent",
        variables: { ledgerId: "synthetic/books", dirPath: "docs" },
      },
      {
        name: "GetLedgerFile",
        variables: { ledgerId: "synthetic/books", path: "docs/{2026}.pdf" },
      },
    ]);

    await user.click(
      screen.getByRole("link", { name: "Open scoped file reference" }),
    );
    await waitFor(() =>
      expect(router.state.location.search).toEqual({
        time: "2026",
        filter: 'document:"{2026}.pdf"',
      }),
    );
    const publicUrl = new URL(
      router.state.location.href,
      window.location.origin,
    );
    expect(publicUrl.pathname).toBe(
      "/ledger/synthetic/books/files/blob/main/docs/%7B2026%7D.pdf",
    );
    expect(publicUrl.searchParams.get("filter")).toBe('document:"{2026}.pdf"');
    expect(publicUrl.hash).toBe("#diff-file-docs%2F%7B2026%7D.pdf");
    expect(
      screen.getByRole("heading", { name: "docs/{2026}.pdf" }),
    ).toBeVisible();
    const reference = JSON.parse(
      screen.getByLabelText("File query and fragment").textContent!,
    ) as { search: Record<string, string>; hash: string };
    expect(reference.search).toEqual({
      time: "2026",
      filter: 'document:"{2026}.pdf"',
    });
    expect(decodeURIComponent(reference.hash)).toBe(
      "diff-file-docs/{2026}.pdf",
    );
    expect(requests).toHaveLength(2);

    await act(async () => {
      history.back();
      await router.load();
    });
    await waitFor(() => expect(router.state.location.search).toEqual({}));
    expect(router.state.location.hash).toBe("");
    expect(screen.getByLabelText("Synthetic file body")).toHaveTextContent(
      "Synthetic PDF body for the {2026} receipt.",
    );
    expect(requests).toHaveLength(2);
  });
});
