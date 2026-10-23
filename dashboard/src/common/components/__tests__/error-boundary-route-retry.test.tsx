import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  Outlet,
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  useLocation,
  useRouter,
} from "@tanstack/react-router";
import { describe, expect, it, vi } from "vitest";
import { ErrorBoundary } from "../error-boundary";

/**
 * A child route whose loader failed is retained in the router; clearing a
 * React boundary alone re-throws the same error. The ledger layout's boundary
 * wiring — onRetry: router.invalidate, resetKey: pathname — reruns it
 * (w4/264).
 */
function LedgerShell() {
  const router = useRouter();
  const location = useLocation();
  return (
    <ErrorBoundary
      resetKey={location.pathname}
      onRetry={() => router.invalidate()}
    >
      <Outlet />
    </ErrorBoundary>
  );
}

async function mount(load: () => Promise<void>) {
  const root = createRootRoute({ component: LedgerShell });
  const commit = createRoute({
    getParentRoute: () => root,
    path: "/ledger/qa/books/commit/$sha",
    loader: load,
    component: () => <h1>Commit detail</h1>,
  });
  const files = createRoute({
    getParentRoute: () => root,
    path: "/ledger/qa/books/files",
    component: () => <h1>Files</h1>,
  });
  const router = createRouter({
    routeTree: root.addChildren([commit, files]),
    history: createMemoryHistory({
      initialEntries: ["/ledger/qa/books/files"],
    }),
  });
  await router.load();
  render(<RouterProvider router={router} />);
  await screen.findByRole("heading", { name: "Files" });
  return router;
}

describe("ledger section retry after a failed loader", () => {
  it("reruns the loader and shows the commit once the read succeeds", async () => {
    let online = false;
    const load = vi.fn(async () => {
      if (!online) throw new TypeError("Failed to fetch");
    });
    const router = await mount(load);
    await router.navigate({
      to: "/ledger/qa/books/commit/$sha",
      params: { sha: "abc" },
    });
    const retry = await screen.findByRole("button", { name: "Try Again" });
    expect(load).toHaveBeenCalledTimes(1);

    online = true;
    retry.focus();
    await userEvent.setup().keyboard("{Enter}");
    expect(
      await screen.findByRole("heading", { name: "Commit detail" }),
    ).toBeInTheDocument();
    expect(load).toHaveBeenCalledTimes(2);
  });

  it("stays actionable when the retry fails again", async () => {
    const load = vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    });
    const router = await mount(load);
    await router.navigate({
      to: "/ledger/qa/books/commit/$sha",
      params: { sha: "abc" },
    });
    await userEvent
      .setup()
      .click(await screen.findByRole("button", { name: "Try Again" }));
    await waitFor(() => expect(load).toHaveBeenCalledTimes(2));
    expect(
      await screen.findByRole("button", { name: "Try Again" }),
    ).toBeInTheDocument();
  });
});
