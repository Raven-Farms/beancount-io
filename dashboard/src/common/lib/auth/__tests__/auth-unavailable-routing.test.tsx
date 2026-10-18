/**
 * w3/646: a brief API outage must not sign the user out in the UI.
 *
 * Drives a real TanStack router whose root `beforeLoad` runs the real
 * `fetchUserProfile` against a stub Apollo client, exactly as `__root.tsx`
 * does, and whose error boundary is the real root `ErrorPage`.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  Outlet,
  RouterProvider,
  createMemoryHistory,
  createRootRouteWithContext,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { CombinedGraphQLErrors } from "@apollo/client/errors";

vi.mock("@/common/apollo/client", () => ({ getClient: vi.fn() }));

import { requireAuth } from "../auth";
import { fetchUserProfile, toAuthContext } from "@/common/server-fn/user";
import ErrorPage from "@/common/root-route/error-page";

afterEach(cleanup);

const unavailableError = () =>
  new CombinedGraphQLErrors({
    errors: [{ message: "502", extensions: { code: "SERVICE_UNAVAILABLE" } }],
  });

function buildRouter(query: ReturnType<typeof vi.fn>) {
  const client = { query } as never;
  const rootRoute = createRootRouteWithContext<{
    userProfile: unknown;
    authStatus?: string;
    authErrorKey?: string;
  }>()({
    beforeLoad: async () => toAuthContext(await fetchUserProfile(client)),
    component: () => <Outlet />,
    errorComponent: ErrorPage,
  });

  const indexRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/",
    component: () => <div>Home</div>,
  });
  const settingsRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/settings",
    beforeLoad: requireAuth("/settings"),
    component: () => <div data-testid="settings">Settings page</div>,
  });
  const loginRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/auth/login",
    validateSearch: (search: Record<string, unknown>) => search,
    component: function LoginRoute() {
      const search = loginRoute.useSearch() as { next?: string };
      return <output data-testid="login-next">{search.next ?? ""}</output>;
    },
  });

  return createRouter({
    routeTree: rootRoute.addChildren([indexRoute, settingsRoute, loginRoute]),
    history: createMemoryHistory({ initialEntries: ["/settings"] }),
    context: { userProfile: undefined },
  });
}

describe("protected routes during a GetCurrentUser outage (w3/646)", () => {
  it("stays on the URL with a retryable service-unavailable state, then recovers via Try Again", async () => {
    const user = userEvent.setup();
    const query = vi.fn(async () => {
      throw unavailableError();
    });
    const router = buildRouter(query);
    render(<RouterProvider router={router as never} />);

    expect(
      await screen.findByText(/service is temporarily unavailable/i),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/settings");
    expect(screen.queryByTestId("login-next")).not.toBeInTheDocument();

    // The API recovers; Try Again re-runs the route in place.
    query.mockImplementation(async () => ({
      data: { userProfile: { id: "u1", email: "qa@example.com" } },
    }));
    await user.click(screen.getByRole("button", { name: /try again/i }));

    expect(await screen.findByTestId("settings")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/settings");
  });

  it("still redirects a genuine signed-out visitor to login with next", async () => {
    const query = vi.fn(async () => ({ data: { userProfile: null } }));
    const router = buildRouter(query);
    render(<RouterProvider router={router as never} />);

    const next = await screen.findByTestId("login-next");
    await waitFor(() => expect(next.textContent).toBe("/settings"));
    expect(router.state.location.pathname).toBe("/auth/login");
  });

  it("lets a signed-in visitor straight through", async () => {
    const query = vi.fn(async () => ({
      data: { userProfile: { id: "u1", email: "qa@example.com" } },
    }));
    const router = buildRouter(query);
    render(<RouterProvider router={router as never} />);

    expect(await screen.findByTestId("settings")).toBeInTheDocument();
  });
});
