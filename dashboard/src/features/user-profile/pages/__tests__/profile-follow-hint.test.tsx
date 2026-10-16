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
import type { FormattedExecutionResult } from "graphql";
import { afterEach, describe, expect, it, vi } from "vitest";
import { toast } from "sonner";
import type { GetUserProfileQuery } from "@/graphql/definitions";
import { createLocalization } from "@/i18n/init";
import { LocalizationProvider } from "@/i18n/provider";
import UserProfilePage from "../user-profile-page";

vi.unmock("react-i18next");
vi.unmock("@/common/hooks/use-translations");
vi.unmock("@/i18n");

// The follow controls, profile query and mutation hooks remain real; unrelated
// navigation chrome and profile tabs do not participate in this state boundary.
vi.mock("../../components/user-profile-header", () => ({
  UserProfileHeader: () => null,
}));
vi.mock("../../components/user-profile-tabs", () => ({
  UserProfileTabs: () => null,
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const messages = {
  en: {
    follow: "Follow",
    unfollow: "Unfollow",
    add: "Add this profile to your following list.",
    remove: "Remove this profile from your following list.",
  },
  de: {
    follow: "Folgen",
    unfollow: "Nicht mehr folgen",
    add: "Fügen Sie dieses Profil Ihrer Folgen-Liste hinzu.",
    remove: "Entfernen Sie dieses Profil aus Ihrer Folgen-Liste.",
  },
};

function profileResult(isFollowing: boolean | null): GetUserProfileQuery {
  return {
    getUserProfile: {
      __typename: "PublicUserProfileResponse",
      isFollowing,
      profile: {
        __typename: "UserProfile",
        username: "alice",
        fullName: "Alice",
        avatarUrl: null,
        bio: null,
        location: null,
        website: null,
        followersCount: 4,
        followingCount: 2,
        starredReposCount: 0,
        created: null,
      },
      activities: [],
      repositories: [],
    },
  };
}

type Request = {
  name: string;
  variables: Record<string, unknown>;
  respond: (result: FormattedExecutionResult) => void;
  reject: (error: Error) => void;
};
const clients: ApolloClient[] = [];

afterEach(() => {
  cleanup();
  clients.splice(0).forEach((client) => client.stop());
  vi.clearAllMocks();
});

async function setup(language: "en" | "de" = "en", viewer = "viewer") {
  const requests: Request[] = [];
  const client = new ApolloClient({
    cache: new InMemoryCache(),
    link: new ApolloLink(
      (operation) =>
        new Observable((observer) => {
          requests.push({
            name: operation.operationName,
            variables: operation.variables,
            respond(result) {
              observer.next(result);
              observer.complete();
            },
            reject(error) {
              observer.error(error);
            },
          });
        }),
    ),
  });
  clients.push(client);
  const localization = createLocalization();
  await localization.changeLanguage(language);
  const root = createRootRouteWithContext<{
    userProfile: { username: string };
  }>()({
    component: () => (
      <LocalizationProvider localization={localization}>
        <ApolloProvider client={client}>
          <Outlet />
        </ApolloProvider>
      </LocalizationProvider>
    ),
  });
  const profile = createRoute({
    getParentRoute: () => root,
    path: "/ledger/$username",
    component: UserProfilePage,
  });
  const router = createRouter({
    routeTree: root.addChildren([profile]),
    history: createMemoryHistory({ initialEntries: ["/ledger/alice"] }),
    context: { userProfile: { username: viewer } },
  });
  await router.load();
  render(<RouterProvider router={router} />);
  await waitFor(() => expect(requests).toHaveLength(1));
  expect(requests[0]).toMatchObject({
    name: "GetUserProfile",
    variables: { username: "alice" },
  });
  return { requests };
}

describe("profile follow hint matches the real follow control", () => {
  it.each([
    { language: "en", initialFollowing: false },
    { language: "en", initialFollowing: true },
    { language: "de", initialFollowing: false },
    { language: "de", initialFollowing: true },
  ] as const)(
    "$language updates button and hint from initial following=$initialFollowing before the refetch completes",
    async ({ language, initialFollowing }) => {
      const { requests } = await setup(language);
      const copy = messages[language];
      const expectState = (following: boolean) => {
        const button = screen.getByRole("button", {
          name: following ? copy.unfollow : copy.follow,
          exact: true,
        });
        expect(button).toHaveAccessibleDescription(
          following ? copy.remove : copy.add,
        );
        expect(
          screen.getByText(following ? copy.remove : copy.add, { exact: true }),
        ).toBeInTheDocument();
        expect(
          screen.queryByText(following ? copy.add : copy.remove, {
            exact: true,
          }),
        ).not.toBeInTheDocument();
        return button;
      };
      await act(async () =>
        requests[0].respond({ data: profileResult(initialFollowing) }),
      );
      const button = expectState(initialFollowing);
      expect(button).toBeEnabled();
      const user = userEvent.setup();
      await user.click(button);
      await waitFor(() => expect(requests).toHaveLength(2));
      expect(requests[1]).toMatchObject({
        name: initialFollowing ? "UnfollowUser" : "FollowUser",
        variables: { username: "alice" },
      });
      expect(expectState(initialFollowing)).toBeDisabled();

      const mutation = initialFollowing ? "unfollowUser" : "followUser";
      await act(async () =>
        requests[1].respond({
          data: {
            [mutation]: {
              __typename: "FollowUserResponse",
              success: true,
              isFollowing: !initialFollowing,
              message: null,
            },
          },
        }),
      );
      await waitFor(() => expect(requests).toHaveLength(3));
      expect(requests[2]).toMatchObject({
        name: "GetUserProfile",
        variables: { username: "alice" },
      });
      // The real mutation starts this refetch, but no server response has arrived.
      await waitFor(() => expect(expectState(!initialFollowing)).toBeEnabled());
      await act(async () =>
        requests[2].respond({ data: profileResult(!initialFollowing) }),
      );
      expect(expectState(!initialFollowing)).toBeEnabled();
      expect(requests).toHaveLength(3);
    },
  );

  it.each([
    { initialFollowing: false, failure: "network" },
    { initialFollowing: true, failure: "unsuccessful response" },
  ] as const)(
    "preserves the confirmed button and hint after $failure",
    async ({ initialFollowing, failure }) => {
      const { requests } = await setup();
      await act(async () =>
        requests[0].respond({ data: profileResult(initialFollowing) }),
      );
      const buttonName = initialFollowing
        ? messages.en.unfollow
        : messages.en.follow;
      const hint = initialFollowing ? messages.en.remove : messages.en.add;
      const oppositeHint = initialFollowing
        ? messages.en.add
        : messages.en.remove;
      await userEvent.click(
        screen.getByRole("button", { name: buttonName, exact: true }),
      );
      await waitFor(() => expect(requests).toHaveLength(2));
      const consoleError = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});
      try {
        if (failure === "network") {
          await act(async () =>
            requests[1].reject(new Error("Controlled network failure")),
          );
        } else {
          await act(async () =>
            requests[1].respond({
              data: {
                unfollowUser: {
                  __typename: "FollowUserResponse",
                  success: false,
                  isFollowing: true,
                  message: "Controlled refusal",
                },
              },
            }),
          );
        }
        await waitFor(() => expect(toast.error).toHaveBeenCalledOnce());
        expect(
          screen.getByRole("button", { name: buttonName, exact: true }),
        ).toBeEnabled();
        expect(screen.getByText(hint, { exact: true })).toBeInTheDocument();
        expect(
          screen.queryByText(oppositeHint, { exact: true }),
        ).not.toBeInTheDocument();
        if (failure === "unsuccessful response") {
          expect(requests).toHaveLength(3);
          await act(async () =>
            requests[2].respond({ data: profileResult(initialFollowing) }),
          );
          expect(screen.getByText(hint, { exact: true })).toBeInTheDocument();
        } else {
          expect(requests).toHaveLength(2);
        }
      } finally {
        consoleError.mockRestore();
      }
    },
  );

  it("renders no follow-state copy in the initial profile skeleton", async () => {
    await setup();
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(
      screen.queryByText(messages.en.add, { exact: true }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(messages.en.remove, { exact: true }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /^(Follow|Unfollow)$/ }),
    ).not.toBeInTheDocument();
  });

  it("withholds the hint while the server's follow state is unknown", async () => {
    const { requests } = await setup();
    await act(async () => requests[0].respond({ data: profileResult(null) }));
    expect(
      await screen.findByRole("heading", { name: "Alice", level: 1 }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: messages.en.follow, exact: true }),
    ).not.toHaveAttribute("aria-describedby");
    expect(
      screen.queryByText(messages.en.add, { exact: true }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(messages.en.remove, { exact: true }),
    ).not.toBeInTheDocument();
  });

  it("offers neither a follow control nor a follow hint on the viewer's own profile", async () => {
    const { requests } = await setup("en", "alice");
    await act(async () => requests[0].respond({ data: profileResult(false) }));
    expect(
      await screen.findByRole("heading", { name: "Alice", level: 1 }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /^(Follow|Unfollow)$/ }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(messages.en.add, { exact: true }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(messages.en.remove, { exact: true }),
    ).not.toBeInTheDocument();
  });
});
