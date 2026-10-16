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
  fireEvent,
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
  useSearch,
} from "@tanstack/react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import type {
  GetUserFollowersQuery,
  GetUserFollowingQuery,
  GetUserStarredReposQuery,
} from "@/graphql/definitions";
import { createLocalization } from "@/i18n/init";
import en from "@/i18n/locales/en";
import de from "@/i18n/locales/de";
import { LocalizationProvider } from "@/i18n/provider";
import { UserProfileTabs } from "../user-profile-tabs";

vi.unmock("@/common/hooks/use-translations");
vi.unmock("react-i18next");

type Tab = "followers" | "following" | "starred";
type Page =
  | GetUserFollowersQuery
  | GetUserFollowingQuery
  | GetUserStarredReposQuery;
interface Request {
  name: string;
  variables: Record<string, unknown>;
  resolve: (data: Page) => void;
  reject: () => void;
}
const clients: ApolloClient[] = [];
afterEach(() => {
  cleanup();
  clients.splice(0).forEach((client) => client.stop());
});

function page(tab: Tab, start: number, count: number, prefix = "person"): Page {
  if (tab === "starred") {
    return {
      getUserStarredRepos: {
        __typename: "RepositoryListResponse",
        total: 47,
        repositories: Array.from({ length: count }, (_, offset) => ({
          __typename: "RepositoryListItem",
          name: `books-${start + offset}`,
          fullName: `author/books-${start + offset}`,
          description: `Ledger ${start + offset}`,
          isPrivate: false,
          updatedAt: "2026-09-01T12:00:00Z",
          starsCount: 1,
        })),
      },
    };
  }
  const data = {
    __typename: "UserListResponse" as const,
    total: 47,
    users: Array.from({ length: count }, (_, offset) => ({
      __typename: "UserListItem" as const,
      username: `${prefix}-${start + offset}`,
      fullName: `Person ${start + offset}`,
      avatarUrl: null,
      bio: `Bio ${start + offset}`,
    })),
  };
  return tab === "followers"
    ? { getUserFollowers: data }
    : { getUserFollowing: data };
}

async function mount(tab: Tab, language: "en" | "de" = "en") {
  const requests: Request[] = [];
  const client = new ApolloClient({
    cache: new InMemoryCache(),
    link: new ApolloLink(
      (operation) =>
        new Observable((observer) => {
          requests.push({
            name: operation.operationName,
            variables: { ...operation.variables },
            resolve: (data) => {
              observer.next({ data });
              observer.complete();
            },
            reject: () =>
              observer.error(new Error("Social network unavailable")),
          });
        }),
    ),
  });
  clients.push(client);
  const localization = createLocalization();
  await localization.changeLanguage(language);
  function Profile() {
    const { username } = useParams({ strict: false });
    const search = useSearch({ strict: false });
    return (
      <>
        <UserProfileTabs
          username={username!}
          activities={[]}
          repositories={[]}
          followersCount={47}
          followingCount={47}
          starredReposCount={47}
          initialTab={search.tab}
        />
        <button>Outside list</button>
      </>
    );
  }
  const root = createRootRoute({ component: Outlet });
  const profile = createRoute({
    getParentRoute: () => root,
    path: "/ledger/$username",
    component: Profile,
    validateSearch: (search: Record<string, unknown>) => ({
      tab: typeof search.tab === "string" ? search.tab : tab,
    }),
  });
  const ledger = createRoute({
    getParentRoute: () => root,
    path: "/ledger/$ledgerOwner/$ledgerName",
    component: () => null,
  });
  const router = createRouter({
    routeTree: root.addChildren([profile, ledger]),
    history: createMemoryHistory({
      initialEntries: [`/ledger/alice?tab=${tab}`],
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
  expect(requests[0].name).toBe(
    {
      followers: "GetUserFollowers",
      following: "GetUserFollowing",
      starred: "GetUserStarredRepos",
    }[tab],
  );
  expect(requests[0].variables).toEqual({
    username: "alice",
    page: 1,
    limit: 20,
  });
  return {
    requests,
    router,
    user: userEvent.setup(),
    messages: language === "en" ? en : de,
  };
}
async function resolve(request: Request, data: Page) {
  await act(async () => request.resolve(data));
}
function expectRows(tab: Tab, count: number) {
  const links = within(screen.getByRole("tabpanel")).getAllByRole("link");
  expect(links).toHaveLength(count);
  links.forEach((link, index) => {
    expect(link).toHaveAttribute(
      "href",
      tab === "starred"
        ? `/ledger/author/books-${index}`
        : `/ledger/person-${index}`,
    );
    expect(link).toHaveTextContent(
      tab === "starred" ? `books-${index}` : `Person ${index}`,
    );
  });
  return links;
}

describe("social continuation with real Apollo, router and localization", () => {
  it.each([
    ["followers", "en"],
    ["following", "de"],
    ["starred", "en"],
  ] as const)(
    "%s keeps the same focused control through a failed page, retry, more results and the end (%s)",
    async (tab, language) => {
      const { requests, user, messages } = await mount(tab, language);
      await resolve(requests[0], page(tab, 0, 20));
      const first = expectRows(tab, 20);
      const more = screen.getByRole("button", {
        name: messages["userProfile.showMore"],
      });
      act(() => more.focus());
      await user.keyboard("{Enter}");
      await waitFor(() => expect(requests).toHaveLength(2));
      expect(more).toBeEnabled();
      expect(more).toHaveAttribute("aria-disabled", "true");
      expect(more).toHaveFocus();
      expect(screen.getByRole("status")).toHaveTextContent(
        messages["common.loading"],
      );
      fireEvent.click(more);
      await user.keyboard("{Enter}");
      expect(requests).toHaveLength(2);
      await act(async () => requests[1].reject());
      expect(await screen.findByRole("alert")).toHaveTextContent(
        messages["userProfile.loadMoreError"],
      );
      const retry = screen.getByRole("button", {
        name: messages["common.tryAgain"],
      });
      expect(retry).toBe(more);
      expect(retry).toHaveFocus();
      expectRows(tab, 20);
      await user.keyboard("{Enter}");
      await waitFor(() => expect(requests).toHaveLength(3));
      expect(requests[2].variables).toEqual(requests[1].variables);
      await resolve(requests[2], page(tab, 20, 20));
      await waitFor(() => expectRows(tab, 40));
      expect(expectRows(tab, 40).slice(0, 20)).toEqual(first);
      expect(more).toHaveFocus();
      expect(more).toHaveAttribute("aria-disabled", "false");
      expect(screen.getByRole("status")).toHaveTextContent(
        language === "en"
          ? "Loaded 20 more items"
          : "20 weitere Einträge geladen",
      );
      await user.keyboard("{Enter}");
      await waitFor(() => expect(requests).toHaveLength(4));
      expect(requests[3].variables).toEqual({
        username: "alice",
        page: 3,
        limit: 20,
      });
      await resolve(requests[3], page(tab, 40, 7));
      await waitFor(() => expectRows(tab, 47));
      expect(more).not.toBeInTheDocument();
      expect(screen.getByRole("status")).toHaveFocus();
      expect(screen.getByRole("status")).toHaveTextContent(
        language === "en"
          ? "Loaded 7 more items No more results"
          : "7 weitere Einträge geladen Keine weiteren Ergebnisse",
      );
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    },
  );

  it("does not steal focus after Tab and ignores a former username's in-flight page", async () => {
    const { requests, router, user } = await mount("followers");
    await resolve(requests[0], page("followers", 0, 20));
    const more = screen.getByRole("button", {
      name: en["userProfile.showMore"],
    });
    act(() => more.focus());
    await user.keyboard("{Enter}{Tab}");
    const outside = screen.getByRole("button", { name: "Outside list" });
    expect(outside).toHaveFocus();
    await resolve(requests[1], page("followers", 20, 7));
    await waitFor(() => expectRows("followers", 27));
    expect(outside).toHaveFocus();

    await act(async () => {
      await router.navigate({
        to: "/ledger/$username",
        params: { username: "bob" },
        search: { tab: "followers" },
      });
    });
    await waitFor(() => expect(requests).toHaveLength(3));
    await resolve(requests[2], page("followers", 0, 20));
    await user.click(
      screen.getByRole("button", { name: en["userProfile.showMore"] }),
    );
    await waitFor(() => expect(requests).toHaveLength(4));
    await act(async () => {
      await router.navigate({
        to: "/ledger/$username",
        params: { username: "carol" },
        search: { tab: "followers" },
      });
    });
    await waitFor(() => expect(requests).toHaveLength(5));
    await resolve(requests[4], page("followers", 0, 20, "current"));
    await resolve(requests[3], page("followers", 20, 7, "stale"));
    expect(
      within(screen.getByRole("tabpanel")).getAllByRole("link"),
    ).toHaveLength(20);
    expect(screen.queryByText("@stale-20")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toBeEmptyDOMElement();
    expect(
      screen.getByRole("button", { name: en["userProfile.showMore"] }),
    ).toHaveAttribute("aria-disabled", "false");
  });
});
