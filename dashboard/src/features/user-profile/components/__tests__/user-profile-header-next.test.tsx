import { render, screen } from "@testing-library/react";
import {
  Outlet,
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { describe, expect, it, vi } from "vitest";
import { UserProfileHeader } from "../user-profile-header";

vi.mock("@/common/hooks/use-is-authenticated", () => ({
  useIsAuthenticated: () => false,
}));
vi.mock("@/common/hooks/use-auth-status", () => ({
  useAuthStatus: () => "signedOut",
}));
vi.mock("@/common/components/user-nav", () => ({ UserNav: () => null }));

/** Header sign-in/up returns to the profile, tab and fragment (w4/237). */
describe("UserProfileHeader signed out", () => {
  it("carries the current profile location as next", async () => {
    const root = createRootRoute({ component: Outlet });
    const profile = createRoute({
      getParentRoute: () => root,
      path: "/ledger/$ledgerOwner",
      validateSearch: (search: Record<string, unknown>) => search,
      component: UserProfileHeader,
    });
    const auth = ["/auth/login", "/auth/sign-up", "/ledger"].map((path) =>
      createRoute({
        getParentRoute: () => root,
        path,
        validateSearch: (search: Record<string, unknown>) => search,
      }),
    );
    const router = createRouter({
      routeTree: root.addChildren([profile, ...auth]),
      history: createMemoryHistory({
        initialEntries: ["/ledger/open_ledger?tab=followers#main-content"],
      }),
    });
    render(<RouterProvider router={router} />);

    const next = encodeURIComponent(
      "/ledger/open_ledger?tab=followers#main-content",
    );
    expect(
      await screen.findByRole("link", { name: "Sign In" }),
    ).toHaveAttribute("href", `/auth/login?next=${next}`);
    expect(screen.getByRole("link", { name: "Sign Up" })).toHaveAttribute(
      "href",
      `/auth/sign-up?next=${next}`,
    );
  });
});
