import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  Outlet,
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { describe, expect, it, vi } from "vitest";
import EntryPage from "../entry-page";

vi.mock("@/common/hooks/use-ledger", () => ({
  useLedger: () => ({ ledgerName: "books" }),
}));
vi.mock("@/features/journal/components/entry-context-panel", () => ({
  EntryContextPanel: ({
    onDirtyChange,
    onSaved,
  }: {
    onDirtyChange?: (dirty: boolean) => void;
    onSaved?: (hash: string) => void | Promise<void>;
  }) => (
    <>
      <button type="button" onClick={() => onDirtyChange?.(true)}>
        edit source
      </button>
      <button type="button" onClick={() => void onSaved?.("def456")}>
        save as new hash
      </button>
    </>
  ),
}));

/** Leaving a standalone entry page with unsaved source edits asks first (w4/250). */
async function mount() {
  const root = createRootRoute({ component: Outlet });
  const entry = createRoute({
    getParentRoute: () => root,
    path: "/ledger/$ledgerOwner/$ledgerName/entry/$entryHash",
    component: EntryPage,
  });
  const journal = createRoute({
    getParentRoute: () => root,
    path: "/ledger/$ledgerOwner/$ledgerName/journal",
    component: () => <h1>Journal destination</h1>,
  });
  const router = createRouter({
    routeTree: root.addChildren([entry, journal]),
    history: createMemoryHistory({
      initialEntries: ["/ledger/qa/books/entry/abc123"],
    }),
  });
  await router.load();
  render(<RouterProvider router={router} />);
  return { router, user: userEvent.setup() };
}

const back = () => screen.getByRole("link", { name: "Back to journal" });

describe("EntryPage unsaved source guard", () => {
  it("asks before leaving a dirty draft, keeps it, then discards on request", async () => {
    const { router, user } = await mount();
    await user.click(
      await screen.findByRole("button", { name: "edit source" }),
    );

    await user.click(back());
    expect(await screen.findByText("Discard your edit?")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Keep editing" }));
    await waitFor(() =>
      expect(screen.queryByText("Discard your edit?")).toBeNull(),
    );
    expect(router.state.location.pathname).toBe(
      "/ledger/qa/books/entry/abc123",
    );

    await user.click(back());
    await user.click(await screen.findByRole("button", { name: /^Discard/ }));
    expect(
      await screen.findByRole("heading", { name: "Journal destination" }),
    ).toBeInTheDocument();
  });

  it("leaves a clean page immediately", async () => {
    await mount();
    await userEvent
      .setup()
      .click(await screen.findByRole("link", { name: "Back to journal" }));
    expect(
      await screen.findByRole("heading", { name: "Journal destination" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Discard your edit?")).toBeNull();
  });

  it("moves to the saved entry's new address without asking (w4/251)", async () => {
    const { router, user } = await mount();
    await user.click(
      await screen.findByRole("button", { name: "edit source" }),
    );
    await user.click(screen.getByRole("button", { name: "save as new hash" }));

    await waitFor(() =>
      expect(router.state.location.pathname).toBe(
        "/ledger/qa/books/entry/def456",
      ),
    );
    expect(screen.queryByText("Discard your edit?")).toBeNull();
  });
});
