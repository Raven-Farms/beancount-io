import {
  ApolloClient,
  ApolloLink,
  InMemoryCache,
  Observable,
} from "@apollo/client";
import { ApolloProvider } from "@apollo/client/react";
import { CombinedGraphQLErrors } from "@apollo/client/errors";
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  Outlet,
  RouterProvider,
  createMemoryHistory,
  createRootRouteWithContext,
  createRoute,
  createRouter,
  isNotFound,
  isRedirect,
} from "@tanstack/react-router";
import { GraphQLError, type FormattedExecutionResult } from "graphql";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { RouterContext } from "@/common/types/router-context";
import { GetUserProfileDocument } from "@/graphql/definitions";
import { createLocalization } from "@/i18n/init";
import { userProfileLoader } from "../loader";
import UserProfilePage from "../pages/user-profile-page";

vi.mock("../components/user-profile-header", () => ({
  UserProfileHeader: () => null,
}));
vi.mock("../components/user-profile-tabs", () => ({
  UserProfileTabs: () => null,
}));
vi.mock("../components/follow-button", () => ({
  FollowButton: () => null,
}));

const profileResult: FormattedExecutionResult = {
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
        followersCount: 0,
        followingCount: 0,
        starredReposCount: 0,
        created: null,
      },
      activities: [],
      repositories: [],
    },
  },
};

function gqlFailure(
  code: string,
  message = "Lookup failed",
): FormattedExecutionResult {
  return { errors: [new GraphQLError(message, { extensions: { code } })] };
}

const clients: ApolloClient[] = [];
function api(initialResult = profileResult) {
  let result = initialResult;
  const requests = vi.fn();
  const client = new ApolloClient({
    cache: new InMemoryCache(),
    link: new ApolloLink((operation) => {
      requests(operation.variables);
      return new Observable((observer) => {
        observer.next(result);
        observer.complete();
      });
    }),
  });
  clients.push(client);
  return {
    client,
    requests,
    respondWith(next: FormattedExecutionResult) {
      result = next;
    },
  };
}

function loaderInput(client: ApolloClient) {
  return {
    params: { username: "alice" },
    context: { client, localization: createLocalization() },
    location: { href: "/ledger/alice?tab=followers#people" } as Parameters<
      typeof userProfileLoader
    >[0]["location"],
    abortController: new AbortController(),
    preload: false,
    cause: "enter" as const,
    deps: {},
  };
}

afterEach(() => {
  cleanup();
  clients.splice(0).forEach((client) => client.stop());
});

describe("profile route lookup", () => {
  it("warms the real profile query cache and reuses it on a repeat load", async () => {
    const { client, requests } = api();
    const input = loaderInput(client);
    await expect(userProfileLoader(input)).resolves.toEqual({
      profileExists: true,
    });
    await expect(userProfileLoader(input)).resolves.toEqual({
      profileExists: true,
    });
    expect(requests).toHaveBeenCalledExactlyOnceWith({ username: "alice" });
    expect(
      client.readQuery({
        query: GetUserProfileDocument,
        variables: { username: "alice" },
      }),
    ).toEqual(profileResult.data);
  });

  it("rejects an absent profile even without GraphQL errors", async () => {
    const { client } = api({ data: { getUserProfile: null } });
    const error = await userProfileLoader(loaderInput(client)).catch(
      (error) => error,
    );
    expect(isNotFound(error)).toBe(true);
  });

  it.each(["NOT_FOUND", "BAD_USER_INPUT", "FORBIDDEN"])(
    "classifies a %s result before SSR",
    async (code) => {
      const { client } = api(gqlFailure(code));
      const error = await userProfileLoader(loaderInput(client)).catch(
        (error) => error,
      );
      expect(isNotFound(error)).toBe(true);
    },
  );

  it("redirects an expired session with its safe deep link", async () => {
    const { client } = api(gqlFailure("UNAUTHENTICATED"));
    const error = await userProfileLoader(loaderInput(client)).catch(
      (error) => error,
    );
    expect(isRedirect(error)).toBe(true);
    expect(error.options).toMatchObject({
      to: "/auth/login",
      search: { next: "/ledger/alice?tab=followers#people" },
    });
  });

  it("leaves an internal lookup failure on the error path", async () => {
    const { client } = api(gqlFailure("INTERNAL_SERVER_ERROR"));
    await expect(userProfileLoader(loaderInput(client))).rejects.toBeInstanceOf(
      CombinedGraphQLErrors,
    );
  });
});

async function mountPage(client: ApolloClient) {
  const rootRoute = createRootRouteWithContext<RouterContext>()({
    component: Outlet,
  });
  const profileRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/ledger/$username",
    component: UserProfilePage,
  });
  const dashboardRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/ledger",
  });
  const router = createRouter({
    routeTree: rootRoute.addChildren([profileRoute, dashboardRoute]),
    context: { client, localization: createLocalization(), userProfile: null },
    history: createMemoryHistory({ initialEntries: ["/ledger/alice"] }),
  });
  await router.load();
  await act(async () => {
    render(
      <ApolloProvider client={client}>
        <RouterProvider router={router} />
      </ApolloProvider>,
    );
  });
}

describe("profile lookup failures after navigation or refetch", () => {
  it.each(["NOT_FOUND", "BAD_USER_INPUT", "FORBIDDEN"])(
    "removes retry when a mounted profile refetch returns %s",
    async (code) => {
      const { client, respondWith } = api();
      await mountPage(client);
      expect(
        await screen.findByRole("heading", { name: "Alice" }),
      ).toBeVisible();

      respondWith(gqlFailure(code));
      await act(async () => {
        await client
          .refetchQueries({ include: [GetUserProfileDocument] })
          .catch(() => {});
      });

      expect(
        await screen.findByRole("heading", { name: "User not found" }),
      ).toBeVisible();
      expect(
        screen.getByText("The user @alice could not be found."),
      ).toBeVisible();
      expect(
        screen.getByRole("link", { name: "Go to dashboard" }),
      ).toHaveAttribute("href", "/ledger");
      expect(
        screen.queryByRole("button", { name: "Try again" }),
      ).not.toBeInTheDocument();
      expect(document.querySelector('meta[name="robots"]')).toHaveAttribute(
        "content",
        expect.stringContaining("noindex"),
      );
      expect(document.querySelector('link[rel="canonical"]')).toBeNull();
    },
  );

  it("keeps a retry for a transient failure whose message happens to contain not found", async () => {
    const { client, respondWith } = api(
      gqlFailure("INTERNAL_SERVER_ERROR", "Storage shard not found"),
    );
    await mountPage(client);
    expect(
      await screen.findByRole("heading", { name: "Error loading profile" }),
    ).toBeVisible();
    expect(
      screen.queryByRole("heading", { name: "User not found" }),
    ).not.toBeInTheDocument();

    respondWith(profileResult);
    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Alice" })).toBeVisible(),
    );
  });
});
