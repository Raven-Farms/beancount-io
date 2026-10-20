import { act, waitFor } from "@testing-library/react";
import { hydrateRoot } from "react-dom/client";
import { renderToString } from "react-dom/server";
import {
  Outlet,
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { describe, expect, it, vi } from "vitest";
import { LedgerWriteAccessNotice } from "../ledger-write-access-notice";

vi.mock("@/common/hooks/use-is-authenticated", () => ({
  useIsAuthenticated: () => false,
}));
vi.mock("@/common/hooks/use-ledger", () => ({
  useLedger: () => ({ ledgerData: null }),
}));

/**
 * The server never sees the fragment. After hydration the notice's actual
 * href must carry it, so a new-tab open returns to the same place a click
 * does (w4/244).
 */
function makeRouter(url: string, isServer: boolean) {
  const root = createRootRoute({ component: Outlet });
  const receipt = createRoute({
    getParentRoute: () => root,
    path: "/ledger/$ledgerOwner/$ledgerName/receipt",
    validateSearch: (search: Record<string, unknown>) => search,
    component: () => (
      <LedgerWriteAccessNotice
        title="Upload unavailable"
        signedOut="Sign in to upload."
        readOnly="Read only."
        unresolved="Unknown access."
      />
    ),
  });
  const login = createRoute({
    getParentRoute: () => root,
    path: "/auth/login",
    validateSearch: (search: Record<string, unknown>) => search,
  });
  const router = createRouter({
    routeTree: root.addChildren([receipt, login]),
    history: createMemoryHistory({ initialEntries: [url] }),
    isServer,
  });
  router.ssr = { manifest: undefined };
  return router;
}

describe("LedgerWriteAccessNotice sign-in href", () => {
  it.each([
    [
      "/ledger/open_ledger/stock-example/receipt?time=2026-09#main-content",
      "/ledger/open_ledger/stock-example/receipt?time=2026-09#main-content",
    ],
    [
      "/ledger/open_ledger/stock-example/receipt?time=2026-09",
      "/ledger/open_ledger/stock-example/receipt?time=2026-09",
    ],
  ])("hydrates %s into an href with the full next", async (url, next) => {
    const server = makeRouter(url.split("#")[0], true);
    await server.load();
    const container = document.createElement("div");
    document.body.appendChild(container);
    container.innerHTML = renderToString(<RouterProvider router={server} />);
    const link = container.querySelector("a")!;
    expect(new URL(link.href, "http://x").searchParams.get("next")).toBe(
      url.split("#")[0],
    );

    const client = makeRouter(url, false);
    await client.load();
    const recoverable = vi.fn();
    await act(async () => {
      hydrateRoot(container, <RouterProvider router={client} />, {
        onRecoverableError: recoverable,
      });
    });
    await waitFor(() =>
      expect(
        new URL(link.getAttribute("href")!, "http://x").searchParams.get(
          "next",
        ),
      ).toBe(next),
    );
    expect(container.querySelector("a")).toBe(link);
    expect(recoverable).not.toHaveBeenCalled();
    container.remove();
  });
});
