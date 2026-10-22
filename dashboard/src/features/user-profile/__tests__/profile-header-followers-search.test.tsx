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
  Outlet,
  RouterProvider,
  createMemoryHistory,
  createRootRouteWithContext,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { RouterContext } from "@/common/types/router-context";
import { createLocalization } from "@/i18n/init";
import { LocalizationProvider } from "@/i18n/provider";
import { userProfileSearchSchema } from "../lib/search";
import UserProfilePage from "../pages/user-profile-page";

vi.unmock("react-i18next");
vi.unmock("@/common/hooks/use-translations");

// The social lists and Follow are not under test; nothing here writes.
const emptyList = {
  total: 0,
  loading: false,
  loadingMore: false,
  hasMore: false,
  error: null,
  loadMoreError: null,
  loadMore: vi.fn(),
  retryLoadMore: vi.fn(),
  refetch: vi.fn(),
};
vi.mock("../hooks/use-user-followers", () => ({
  useUserFollowers: () => ({ ...emptyList, followers: [] }),
}));
vi.mock("../hooks/use-user-following", () => ({
  useUserFollowing: () => ({ ...emptyList, following: [] }),
}));
vi.mock("../hooks/use-user-starred-repos", () => ({
  useUserStarredRepos: () => ({ ...emptyList, starredRepos: [] }),
}));
vi.mock("../components/follow-button", () => ({ FollowButton: () => null }));

// Twenty "house" ledgers, newest last, and a few others the search hides.
const repositories = [
  ...Array.from(
    { length: 20 },
    (_, i) => `house-${String(i).padStart(2, "0")}`,
  ),
  "trip-00",
  "trip-01",
].map((name, i) => ({
  __typename: "UserRepository",
  name,
  fullName: `alice/${name}`,
  description: null,
  isPrivate: false,
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: new Date(Date.UTC(2026, 0, i + 1)).toISOString(),
}));

const clients: ApolloClient[] = [];

async function mountProfile() {
  const client = new ApolloClient({
    cache: new InMemoryCache(),
    link: new ApolloLink(
      () =>
        new Observable((observer) => {
          observer.next({
            data: {
              getUserProfile: {
                __typename: "PublicUserProfileResponse",
                isFollowing: false,
                profile: {
                  __typename: "UserProfile",
                  username: "alice",
                  fullName: "Alice",
                  avatarUrl: null,
                  bio: null,
                  location: null,
                  website: null,
                  followersCount: 456,
                  followingCount: 3,
                  starredReposCount: 0,
                  created: null,
                },
                activities: [],
                repositories,
              },
            },
          });
          observer.complete();
        }),
    ),
  });
  clients.push(client);
  const localization = createLocalization();
  const rootRoute = createRootRouteWithContext<RouterContext>()({
    component: Outlet,
  });
  const profileRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/ledger/$username",
    validateSearch: (search) => userProfileSearchSchema.parse(search),
    component: UserProfilePage,
  });
  const ledgerRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/ledger/$ledgerOwner/$ledgerName",
  });
  const router = createRouter({
    routeTree: rootRoute.addChildren([profileRoute, ledgerRoute]),
    context: { client, localization, userProfile: null },
    history: createMemoryHistory({ initialEntries: ["/ledger/alice"] }),
  });
  await router.load();
  await act(async () => {
    render(
      <LocalizationProvider localization={localization}>
        <ApolloProvider client={client}>
          <RouterProvider router={router} />
        </ApolloProvider>
      </LocalizationProvider>,
    );
  });
  await screen.findByRole("searchbox", { name: "Search ledgers…" });
  return router;
}

/** The collection's ledger links, in the order shown. */
const ledgers = () =>
  screen
    .getAllByRole("link")
    .map((link) => link.getAttribute("href") ?? "")
    .filter((href) => href.startsWith("/ledger/alice/"))
    .map((href) => href.slice("/ledger/alice/".length));

/** Searched, sorted by name and revealed past the first page. */
async function narrowCollection(
  router: Awaited<ReturnType<typeof mountProfile>>,
) {
  const user = userEvent.setup();
  await user.type(screen.getByRole("searchbox"), "house");
  await user.tab();
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Sort ledgers" }),
    "name",
  );
  await user.click(screen.getByRole("button", { name: "Show more ledgers" }));
  await waitFor(() =>
    expect(router.state.location.search).toEqual({
      q: "house",
      sort: "name",
      show: 24,
    }),
  );
  expect(ledgers()).toHaveLength(20);
  expect(ledgers()[0]).toBe("house-00");
  return user;
}

async function expectCollectionKept(
  router: Awaited<ReturnType<typeof mountProfile>>,
) {
  await waitFor(() =>
    expect(screen.getByRole("searchbox")).toHaveValue("house"),
  );
  expect(router.state.location.pathname).toBe("/ledger/alice");
  expect(router.state.location.search).toEqual({
    tab: "overview",
    q: "house",
    sort: "name",
    show: 24,
  });
  expect(screen.getByRole("combobox", { name: "Sort ledgers" })).toHaveValue(
    "name",
  );
  expect(ledgers()).toHaveLength(20);
  expect(ledgers()[0]).toBe("house-00");
}

afterEach(() => {
  cleanup();
  clients.splice(0).forEach((client) => client.stop());
});

/** The profile header's followers count keeps the collection's state (w4/336). */
describe("profile header Followers link", () => {
  it("opens Followers with the collection's search, sort and reveal kept for the way back", async () => {
    const router = await mountProfile();
    const user = await narrowCollection(router);

    const header = screen.getByRole("link", { name: "456 followers" });
    expect(header).toHaveAttribute(
      "href",
      "/ledger/alice?q=house&sort=name&show=24&tab=followers",
    );
    await user.click(header);
    await waitFor(() =>
      expect(screen.getByRole("tab", { selected: true })).toHaveTextContent(
        /Followers/,
      ),
    );
    expect(router.state.location.pathname).toBe("/ledger/alice");
    expect(router.state.location.search).toEqual({
      tab: "followers",
      q: "house",
      sort: "name",
      show: 24,
    });

    await user.click(screen.getByRole("tab", { name: "Ledgers" }));
    await expectCollectionKept(router);
  });

  it("matches the Followers tab trigger, which already kept it", async () => {
    const router = await mountProfile();
    const user = await narrowCollection(router);

    await user.click(screen.getByRole("tab", { name: /Followers/ }));
    await waitFor(() =>
      expect(router.state.location.search).toMatchObject({
        tab: "followers",
        q: "house",
      }),
    );
    await user.click(screen.getByRole("tab", { name: "Ledgers" }));
    await expectCollectionKept(router);
  });
});
