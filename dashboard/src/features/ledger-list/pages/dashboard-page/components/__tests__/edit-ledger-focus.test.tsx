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
} from "@tanstack/react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SidebarProvider } from "@/common/components/ui/sidebar";
import { ReactNativeContext } from "@/common/providers/react-native-bridge-provider/react-native-bridge-context";
import { createLocalization } from "@/i18n/init";
import { LocalizationProvider } from "@/i18n/provider";
import { DashboardSidebar } from "../dashboard-sidebar";

vi.unmock("@/common/hooks/use-translations");
vi.unmock("react-i18next");

function ledger(name: string) {
  const repo = name.toLowerCase();
  return {
    __typename: "Ledger" as const,
    id: `alice/${repo}`,
    name,
    fullName: `alice/${repo}`,
    httpUrl: `https://example.invalid/alice/${repo}`,
    sshUrl: `git@example.invalid:alice/${repo}`,
    private: true,
    empty: false,
    size: 42,
    createdAt: "2026-01-01T10:00:00.000Z",
    updatedAt: "2026-01-02T10:00:00.000Z",
    description: `${name} synthetic books`,
    permissions: {
      __typename: "Permission" as const,
      admin: true,
      pull: true,
      push: true,
    },
  };
}
const clients: ApolloClient[] = [];
beforeEach(() => {
  // jsdom has no media-query engine; keep the real sidebar on desktop.
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener() {},
    removeListener() {},
    addEventListener() {},
    removeEventListener() {},
    dispatchEvent: () => false,
  }));
  window.history.replaceState(null, "", "/ledger");
});
afterEach(async () => {
  cleanup();
  // Radix restores focus in a deferred unmount task. Drain it before the
  // following test mounts another menu/dialog and before restoring globals.
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
  clients.splice(0).forEach((client) => client.stop());
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  window.history.replaceState(null, "", "/ledger");
});

async function setup(language: "en" | "de", currentLedger = false) {
  let ledgers = [ledger("First"), ledger("Second")];
  const writes: Array<{ name: string; variables: Record<string, unknown> }> =
    [];
  const requests: string[] = [];
  const client = new ApolloClient({
    cache: new InMemoryCache(),
    link: new ApolloLink(
      (operation) =>
        new Observable((observer) => {
          requests.push(operation.operationName);
          if (operation.operationName === "ListLedgers") {
            observer.next({ data: { listLedgers: ledgers } });
          } else if (operation.operationName === "GetCurrentUser") {
            observer.next({
              data: {
                userProfile: {
                  __typename: "UserProfileResponse",
                  id: "synthetic-user",
                  username: "alice",
                  email: "alice@example.invalid",
                  tier: "FREE",
                  locale: language,
                  firstName: null,
                  lastName: null,
                  emailReportStatus: null,
                  hasEverSubscribed: false,
                  limits: {
                    __typename: "UserLimits",
                    ledgersUsed: 2,
                    ledgersMax: 3,
                    collaboratorsPerLedgerMax: 2,
                    maxDirectives: 1000,
                  },
                },
              },
            });
          } else if (operation.operationName === "UpdateLedger") {
            writes.push({
              name: operation.operationName,
              variables: operation.variables,
            });
            const original = ledgers.find(
              (item) => item.id === operation.variables.ledgerId,
            )!;
            const updated = {
              ...original,
              ...ledger(String(operation.variables.name)),
              description: String(operation.variables.description),
              private: Boolean(operation.variables.private),
            };
            ledgers = ledgers.map((item) =>
              item.id === original.id ? updated : item,
            );
            observer.next({ data: { updateLedger: updated } });
          } else {
            observer.error(
              new Error(`Unexpected operation: ${operation.operationName}`),
            );
            return;
          }
          observer.complete();
        }),
    ),
  });
  clients.push(client);
  const localization = createLocalization();
  await localization.changeLanguage(language);
  const root = createRootRoute({
    component: () => (
      <SidebarProvider>
        <DashboardSidebar />
        <Outlet />
      </SidebarProvider>
    ),
  });
  const dashboard = createRoute({
    getParentRoute: () => root,
    path: "/ledger",
    component: () => <h1>Dashboard destination</h1>,
  });
  const detail = createRoute({
    getParentRoute: () => root,
    path: "/ledger/$ledgerOwner/$ledgerName",
    component: () => <h1>Ledger destination</h1>,
  });
  const initialEntry = currentLedger ? "/ledger/alice/second" : "/ledger";
  window.history.replaceState(null, "", initialEntry);
  const router = createRouter({
    routeTree: root.addChildren([dashboard, detail]),
    history: createMemoryHistory({ initialEntries: [initialEntry] }),
  });
  await router.load();
  render(
    <LocalizationProvider localization={localization}>
      <ReactNativeContext.Provider value={{ isReactNative: false }}>
        <ApolloProvider client={client}>
          <RouterProvider router={router} />
        </ApolloProvider>
      </ReactNativeContext.Provider>
    </LocalizationProvider>,
  );
  await screen.findByText("second");
  const trigger = (name: "first" | "second") => {
    const row = screen.getByText(name).closest("li")!;
    return within(row).getByRole("button", {
      name: localization.i18n.t("common.settings"),
    });
  };
  return { localization, router, writes, requests, trigger };
}

async function openEdit(
  trigger: HTMLElement,
  localization: ReturnType<typeof createLocalization>,
  user: ReturnType<typeof userEvent.setup>,
) {
  act(() => trigger.focus());
  await user.keyboard("{Enter}");
  const edit = await screen.findByRole("menuitem", {
    name: localization.i18n.t("page.dashboard.editLedger"),
  });
  await waitFor(() => expect(edit).toHaveFocus());
  await user.keyboard("{Enter}");
  const dialog = await screen.findByRole("dialog", {
    name: localization.i18n.t("page.dashboard.editLedgerSettings"),
  });
  const name = within(dialog).getByRole("textbox", {
    name: localization.i18n.t("page.dashboard.ledgerName"),
  });
  await waitFor(() => expect(name).toHaveFocus());
  return { dialog, name };
}

describe("dashboard Edit Ledger focus return", () => {
  it.each(
    (["en", "de"] as const).flatMap((language) =>
      (["Escape", "Cancel", "Close"] as const).map(
        (dismissal) => [language, dismissal] as const,
      ),
    ),
  )(
    "returns %s %s to the second ledger's persistent Settings button",
    async (language, dismissal) => {
      const { trigger, localization, writes } = await setup(language);
      const second = trigger("second");
      const first = trigger("first");
      const user = userEvent.setup();
      const { dialog, name } = await openEdit(second, localization, user);
      expect(name).toHaveValue("Second");
      expect(second).toBeInTheDocument();
      expect(screen.queryByRole("menu")).not.toBeInTheDocument();
      if (dismissal === "Escape") await user.keyboard("{Escape}");
      else
        await user.click(
          within(dialog).getByRole("button", {
            name: localization.i18n.t(
              dismissal === "Cancel" ? "common.cancel" : "common.closeDialog",
            ),
          }),
        );
      await waitFor(() =>
        expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
      );
      await waitFor(() => expect(second).toHaveFocus());
      expect(first).not.toHaveFocus();
      expect(writes).toEqual([]);
    },
  );

  it.each(["en", "de"] as const)(
    "preserves the %s menu-only Escape return without opening a dialog",
    async (language) => {
      const { trigger, localization, writes } = await setup(language);
      const second = trigger("second");
      const user = userEvent.setup();
      act(() => second.focus());
      await user.keyboard("{Enter}");
      await screen.findByRole("menuitem", {
        name: localization.i18n.t("page.dashboard.editLedger"),
      });
      await user.keyboard("{Escape}");
      await waitFor(() => expect(second).toHaveFocus());
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
      expect(writes).toEqual([]);
    },
  );

  it.each(["en", "de"] as const)(
    "retains the existing %s Delete Ledger Cancel focus control",
    async (language) => {
      const { trigger, localization, writes } = await setup(language);
      const second = trigger("second");
      const user = userEvent.setup();
      act(() => second.focus());
      await user.keyboard("{Enter}");
      await screen.findByRole("menuitem", {
        name: localization.i18n.t("page.dashboard.editLedger"),
      });
      await user.keyboard("{ArrowDown}{Enter}");
      const dialog = await screen.findByRole("alertdialog", {
        name: localization.i18n.t("page.dashboard.deleteLedger"),
      });
      await user.click(
        within(dialog).getByRole("button", {
          name: localization.i18n.t("common.cancel"),
        }),
      );
      await waitFor(() =>
        expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument(),
      );
      await waitFor(() => expect(second).toHaveFocus());
      expect(writes).toEqual([]);
    },
  );

  it("preserves a successful edit's exact ledger target and stays on the dashboard", async () => {
    const { trigger, localization, writes, router } = await setup("en");
    const user = userEvent.setup();
    const { dialog } = await openEdit(trigger("second"), localization, user);
    const description = within(dialog).getByRole("textbox", {
      name: localization.i18n.t("page.dashboard.descriptionOptional"),
    });
    await user.clear(description);
    await user.type(description, "Updated یادداشت");
    await user.click(
      within(dialog).getByRole("button", {
        name: localization.i18n.t("common.save"),
      }),
    );
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    await screen.findByText("alice · Updated یادداشت");
    expect(writes).toEqual([
      {
        name: "UpdateLedger",
        variables: {
          ledgerId: "alice/second",
          name: "second",
          description: "Updated یادداشت",
          private: true,
        },
      },
    ]);
    expect(router.state.location.pathname).toBe("/ledger");
    expect(trigger("first")).toBeInTheDocument();
    expect(trigger("second")).toBeInTheDocument();
  });

  it("preserves rename navigation without focusing a removed opener and restores the next dialog's own opener", async () => {
    const { trigger, localization, writes, router } = await setup("en", true);
    const second = trigger("second");
    const user = userEvent.setup();
    const { dialog, name } = await openEdit(second, localization, user);
    const restoreOldTrigger = vi.spyOn(second, "focus");
    await user.clear(name);
    await user.type(name, "Renamed Books");
    await user.click(
      within(dialog).getByRole("button", {
        name: localization.i18n.t("common.save"),
      }),
    );
    await waitFor(() =>
      expect(router.state.matches.at(-1)?.params).toMatchObject({
        ledgerOwner: "alice",
        ledgerName: "renamed-books",
      }),
    );
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    await screen.findByText("renamed-books");
    expect(second).not.toBeInTheDocument();
    expect(restoreOldTrigger).not.toHaveBeenCalled();
    expect(writes).toEqual([
      {
        name: "UpdateLedger",
        variables: {
          ledgerId: "alice/second",
          name: "renamed-books",
          description: "Second synthetic books",
          private: true,
        },
      },
    ]);
    // A redirect's close must not suppress focus return on the next edit.
    const first = trigger("first");
    await openEdit(first, localization, user);
    await user.keyboard("{Escape}");
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    await waitFor(() => expect(first).toHaveFocus());
    expect(writes).toHaveLength(1);
  });
});
