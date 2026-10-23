import { act, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { hydrateRoot, type Root } from "react-dom/client";
import { renderToString } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  GetLedgerIntervalTotalsDocument,
  GetLedgerJournalDocument,
} from "@/graphql/definitions";
import { createLocalization } from "@/i18n/init";
import { LocalizationProvider } from "@/i18n/provider";
import LedgerBudgetPage from "../index";

vi.unmock("@/common/hooks/use-translations");
vi.unmock("react-i18next");

// The real useHydrated decides readiness; only the route params are stubbed.
vi.mock("@tanstack/react-router", async () => {
  const { useHydrated } = await vi.importActual<
    typeof import("@tanstack/react-router")
  >("@tanstack/react-router");
  return {
    useHydrated,
    useParams: () => ({ ledgerOwner: "alice", ledgerName: "books" }),
  };
});
vi.mock("@apollo/client/react", () => ({
  useQuery: (document: unknown) =>
    document === GetLedgerJournalDocument
      ? {
          data: {
            getLedgerJournal: {
              total: 1,
              data: [
                {
                  date: "2025-01-01",
                  entry_hash: "synthetic-budget-dining",
                  directive_type: "custom",
                  type: "budget",
                  values: [
                    "Expenses:Dining",
                    "monthly",
                    { number: "200", currency: "USD" },
                  ],
                },
              ],
            },
          },
          loading: false,
        }
      : document === GetLedgerIntervalTotalsDocument
        ? { data: { getLedgerIntervalTotals: [] }, loading: false }
        : { data: undefined, loading: false },
  useApolloClient: () => ({ query: vi.fn() }),
}));
vi.mock("@/common/hooks/use-ledger", () => ({
  useLedger: () => ({
    primaryCurrency: "USD",
    ledgerData: { options: { renderCommas: true } },
  }),
}));
vi.mock("@/common/hooks/use-ledger-permission", () => ({
  useLedgerPermission: () => ({ canWrite: true }),
}));
vi.mock("@/common/components/react-echarts", () => ({
  ReactECharts: () => null,
}));
// The dialog itself is covered by its own tests; here it reports each open.
vi.mock("../add-budget-dialog", () => ({
  AddBudgetDialog: ({ open }: { open: boolean }) =>
    open ? <div role="dialog" aria-label="Add Budget form" /> : null,
}));
vi.mock("../delete-budget-dialog", () => ({ DeleteBudgetDialog: () => null }));

const roots: Root[] = [];
afterEach(() => {
  roots.splice(0).forEach((root) => act(() => root.unmount()));
  document.body.innerHTML = "";
});

/** Server markup first, then real hydration, as a fresh page load does. */
async function serverThenHydrate() {
  const view = (
    <LocalizationProvider localization={createLocalization()}>
      <LedgerBudgetPage />
    </LocalizationProvider>
  );
  const container = document.createElement("div");
  document.body.appendChild(container);
  container.innerHTML = renderToString(view);
  const add = () =>
    [...container.querySelectorAll("button")].find(
      (button) => button.textContent?.trim() === "Add Budget",
    )!;

  // Before hydration the click would open nothing, so it is not offered.
  expect(add()).toBeDisabled();

  const recoverable = vi.fn();
  await act(async () => {
    roots.push(
      hydrateRoot(container, view, { onRecoverableError: recoverable }),
    );
  });
  await waitFor(() => expect(add()).toBeEnabled());
  expect(recoverable).not.toHaveBeenCalled();
  return {
    button: add(),
    dialogs: () => document.querySelectorAll("[role=dialog]"),
  };
}

/** Budget's header Add action waits for its handler (w4/962). */
describe("Budget header Add before and after hydration", () => {
  it.each(["pointer", "Enter", "Space"])(
    "opens exactly one dialog on the first usable %s activation",
    async (input) => {
      const user = userEvent.setup();
      const { button, dialogs } = await serverThenHydrate();
      expect(dialogs()).toHaveLength(0);

      if (input === "pointer") {
        await user.click(button);
      } else {
        button.focus();
        await user.keyboard(input === "Enter" ? "{Enter}" : " ");
      }

      await waitFor(() => expect(dialogs()).toHaveLength(1));
    },
  );
});
