import {
  ApolloClient,
  ApolloLink,
  InMemoryCache,
  Observable,
} from "@apollo/client";
import { ApolloProvider } from "@apollo/client/react";
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  RouterProvider,
  useParams,
} from "@tanstack/react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ListCommitsQuery } from "@/graphql/definitions";
import { createLocalization } from "@/i18n/init";
import en from "@/i18n/locales/en";
import { LocalizationProvider } from "@/i18n/provider";
import CommitsSplitView from "../commits-split-view";

vi.unmock("@/common/hooks/use-translations");
vi.unmock("react-i18next");
vi.mock("../commit-detail", () => ({
  CommitDetail: ({ commitSha }: { commitSha: string }) => (
    <output aria-label="Synthetic commit detail">{commitSha}</output>
  ),
}));

afterEach(cleanup);

const sha = (i: number) => `a${String(i).padStart(3, "0")}${"0".repeat(36)}`;
const page = (start: number, count: number): ListCommitsQuery => ({
  listCommits: Array.from({ length: count }, (_, offset) => ({
    __typename: "CommitListItem",
    sha: sha(start + offset),
    shortSha: sha(start + offset).slice(0, 7),
    message: `Synthetic change ${start + offset}`,
    author: {
      __typename: "CommitAuthor",
      name: "Ada",
      email: "ada@example.com",
      date: "2026-09-01T12:00:00.000Z",
    },
  })),
});

/**
 * Selecting another commit keeps the loaded history pages and cursor; the
 * detail pane shows its own pending state while the commit loads (w4/246).
 */
describe("Version History while another commit loads", () => {
  it("keeps 60 loaded commits and continues with page 3", async () => {
    const pages: Array<{
      page: number;
      resolve: (d: ListCommitsQuery) => void;
    }> = [];
    const client = new ApolloClient({
      cache: new InMemoryCache(),
      link: new ApolloLink(
        (operation) =>
          new Observable((observer) => {
            pages.push({
              page: operation.variables.page as number,
              resolve: (data) => {
                observer.next({ data });
                observer.complete();
              },
            });
          }),
      ),
    });
    let releaseDetail!: () => void;
    const heldDetail = new Promise<void>(
      (resolve) => (releaseDetail = resolve),
    );

    function History() {
      const { ledgerOwner, ledgerName, commitSha } = useParams({
        strict: false,
      });
      return (
        <CommitsSplitView
          ledgerId={`${ledgerOwner}/${ledgerName}`}
          selectedCommitSha={commitSha}
        />
      );
    }
    const root = createRootRoute({ component: History });
    const commitRoute = createRoute({
      getParentRoute: () => root,
      path: "/ledger/$ledgerOwner/$ledgerName/commit/$commitSha",
      // The commit loader: an uncached detail read that takes a while.
      loader: async ({ params }) => {
        if (params.commitSha === sha(31)) await heldDetail;
      },
      component: () => null,
    });
    const router = createRouter({
      routeTree: root.addChildren([commitRoute]),
      history: createMemoryHistory({
        initialEntries: [`/ledger/alice/books/commit/${sha(0)}`],
      }),
    });
    await router.load();
    const localization = createLocalization();
    render(
      <LocalizationProvider localization={localization}>
        <ApolloProvider client={client}>
          <RouterProvider router={router} />
        </ApolloProvider>
      </LocalizationProvider>,
    );
    const user = userEvent.setup();
    await waitFor(() => expect(pages).toHaveLength(1));
    await act(async () => pages[0]!.resolve(page(0, 30)));
    await user.click(
      await screen.findByRole("button", { name: en["commits.loadOlder"] }),
    );
    await waitFor(() => expect(pages).toHaveLength(2));
    await act(async () => pages[1]!.resolve(page(30, 30)));
    await waitFor(() =>
      expect(screen.getAllByTestId("commit-list-item")).toHaveLength(60),
    );
    const firstLink = screen.getAllByTestId("commit-list-item")[0];

    await user.click(screen.getAllByTestId("commit-list-item")[31]!);
    // While sha 31 loads: the history stays, the detail says it is loading.
    await waitFor(() =>
      expect(
        screen.getByRole("region", { name: en["commits.detailTitle"] }),
      ).toHaveAttribute("aria-busy", "true"),
    );
    expect(screen.getAllByTestId("commit-list-item")).toHaveLength(60);
    expect(
      screen.queryByRole("status", { name: "Synthetic commit detail" }),
    ).toBeNull();

    await act(async () => releaseDetail());
    await waitFor(() =>
      expect(
        screen.getByRole("status", { name: "Synthetic commit detail" }),
      ).toHaveTextContent(sha(31)),
    );
    expect(screen.getAllByTestId("commit-list-item")).toHaveLength(60);
    expect(screen.getAllByTestId("commit-list-item")[0]).toBe(firstLink);
    expect(pages).toHaveLength(2);

    await user.click(
      screen.getByRole("button", { name: en["commits.loadOlder"] }),
    );
    await waitFor(() => expect(pages).toHaveLength(3));
    expect(pages[2]!.page).toBe(3);
  });
});
