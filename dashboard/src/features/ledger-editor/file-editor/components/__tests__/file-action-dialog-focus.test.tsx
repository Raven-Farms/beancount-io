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
import { useLayoutEffect, useRef } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useTranslations } from "@/common/hooks/use-translations";
import type { GetLedgerFileQuery } from "@/graphql/definitions";
import { createLocalization } from "@/i18n/init";
import { LocalizationProvider } from "@/i18n/provider";
import { FileActionButtons } from "../non-text-file-views";

vi.unmock("@/common/hooks/use-translations");
vi.unmock("react-i18next");
vi.mock("@/common/hooks/use-is-authenticated", () => ({
  useIsAuthenticated: () => true,
}));
vi.mock("@/common/providers/ledger-provider", () => ({
  useLedger: () => ({
    ledgerData: { permissions: { pull: true, push: true } },
  }),
}));

const file: NonNullable<GetLedgerFileQuery["getLedgerFile"]> = {
  __typename: "LedgerFileContent",
  name: "README.md",
  path: "README.md",
  sha: "synthetic-file-sha",
  size: 12,
  type: "file",
  encoding: "base64",
  content: "IyBTbnRoZXRpYwo=",
  lastCommitSha: null,
  lastAuthorDate: null,
  lastCommitterDate: null,
};

async function drainRadixFocus() {
  // FocusScope restores focus in an unmount task, after the dialog disappears.
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

afterEach(async () => {
  cleanup();
  await drainRadixFocus();
});

function FilesDestination() {
  const { t } = useTranslations();
  const heading = useRef<HTMLHeadingElement>(null);
  useLayoutEffect(() => {
    heading.current?.focus();
  }, []);
  return (
    <h1 ref={heading} tabIndex={-1}>
      {t("ledgerEditor.files")}
    </h1>
  );
}

async function setup(
  language: "en" | "de" = "en",
  deleteNavigation: "none" | "immediate" | "held" = "none",
) {
  const localization = createLocalization();
  await localization.changeLanguage(language);
  let finishDelete!: () => void;
  const pendingDelete = new Promise<void>((resolve) => {
    finishDelete = resolve;
  });
  const onDelete = vi.fn(async () => {
    if (deleteNavigation === "none") return;
    if (deleteNavigation === "held") await pendingDelete;
    await router.navigate({ to: "/files" });
  });
  const root = createRootRoute({ component: () => <Outlet /> });
  const fileRoute = createRoute({
    getParentRoute: () => root,
    path: "/file",
    component: () => (
      <FileActionButtons
        filename={file.name}
        fileContent={file}
        onDownload={vi.fn()}
        onDelete={onDelete}
      />
    ),
  });
  const filesRoute = createRoute({
    getParentRoute: () => root,
    path: "/files",
    component: FilesDestination,
  });
  const router = createRouter({
    routeTree: root.addChildren([fileRoute, filesRoute]),
    history: createMemoryHistory({ initialEntries: ["/file"] }),
  });
  await router.load();
  render(
    <LocalizationProvider localization={localization}>
      <RouterProvider router={router} />
    </LocalizationProvider>,
  );
  const t = localization.i18n.t.bind(localization.i18n);
  const user = userEvent.setup();
  const opener = screen.getByRole("button", { name: t("common.moreActions") });
  async function openMenu() {
    await user.tab();
    expect(opener).toHaveFocus();
    await user.keyboard("{Enter}");
    await screen.findByRole("menu");
  }
  async function openDelete() {
    await openMenu();
    await user.keyboard("{End}");
    expect(
      screen.getByRole("menuitem", { name: t("common.delete") }),
    ).toHaveFocus();
    await user.keyboard("{Enter}");
    const dialog = await screen.findByRole("dialog", {
      name: t("ledgerEditor.deleteFileTitle"),
    });
    expect(dialog).toHaveAccessibleDescription(
      t("ledgerEditor.deleteFileConfirmation", { filename: file.name }),
    );
    await waitFor(() =>
      expect(
        within(dialog).getByRole("button", { name: t("common.cancel") }),
      ).toHaveFocus(),
    );
    return dialog;
  }
  return {
    user,
    t,
    opener,
    onDelete,
    router,
    openMenu,
    openDelete,
    finishDelete,
  };
}

describe("file actions menu-launched Delete dialog focus", () => {
  it.each(
    (["en", "de"] as const).flatMap((language) =>
      (["Escape", "Cancel", "Close"] as const).map(
        (dismissal) => [language, dismissal] as const,
      ),
    ),
  )(
    "returns to the persistent %s More actions trigger after %s",
    async (language, dismissal) => {
      const { user, t, opener, onDelete, openDelete } = await setup(language);
      const dialog = await openDelete();
      if (dismissal === "Escape") {
        await user.keyboard("{Escape}");
      } else if (dismissal === "Cancel") {
        await user.keyboard("{Enter}");
      } else {
        await user.tab({ shift: true });
        expect(
          within(dialog).getByRole("button", { name: t("common.closeDialog") }),
        ).toHaveFocus();
        await user.keyboard("{Enter}");
      }
      await waitFor(() =>
        expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
      );
      await drainRadixFocus();
      expect(opener).toHaveFocus();
      expect(onDelete).not.toHaveBeenCalled();
      await user.keyboard("{Enter}");
      expect(await screen.findByRole("menu")).toBeInTheDocument();
    },
  );

  it("keeps ordinary menu Escape focus restoration without opening Delete", async () => {
    const { user, opener, onDelete, openMenu } = await setup();
    await openMenu();
    await user.keyboard("{Escape}");
    await waitFor(() =>
      expect(screen.queryByRole("menu")).not.toBeInTheDocument(),
    );
    await drainRadixFocus();
    expect(opener).toHaveFocus();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(onDelete).not.toHaveBeenCalled();
  });

  it("leaves focus on the new route after confirmed deletion unmounts the opener", async () => {
    const { user, t, opener, onDelete, router, openDelete } = await setup(
      "en",
      "immediate",
    );
    const dialog = await openDelete();
    await user.tab();
    expect(
      within(dialog).getByRole("button", { name: t("common.delete") }),
    ).toHaveFocus();
    await user.keyboard("{Enter}");
    const heading = await screen.findByRole("heading", {
      level: 1,
      name: t("ledgerEditor.files"),
    });
    await drainRadixFocus();
    expect(onDelete).toHaveBeenCalledTimes(1);
    expect(router.state.location.pathname).toBe("/files");
    expect(opener).not.toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(heading).toHaveFocus();
  });

  it("closes after confirming an asynchronous delete without restoring the dismissed action", async () => {
    const { user, opener, onDelete, router, openDelete, finishDelete, t } =
      await setup("de", "held");
    await openDelete();
    await user.tab();
    await user.keyboard("{Enter}");
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    await drainRadixFocus();
    expect(onDelete).toHaveBeenCalledTimes(1);
    expect(router.state.location.pathname).toBe("/file");
    expect(opener).not.toHaveFocus();

    await act(async () => finishDelete());
    const heading = await screen.findByRole("heading", {
      level: 1,
      name: t("ledgerEditor.files"),
    });
    await drainRadixFocus();
    expect(opener).not.toBeInTheDocument();
    expect(heading).toHaveFocus();
    expect(onDelete).toHaveBeenCalledTimes(1);
  });
});
