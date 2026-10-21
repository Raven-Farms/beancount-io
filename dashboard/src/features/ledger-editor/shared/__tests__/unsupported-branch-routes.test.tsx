import { ApolloClient, ApolloLink, InMemoryCache } from "@apollo/client";
import { cleanup, render, screen } from "@testing-library/react";
import {
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  RouterProvider,
} from "@tanstack/react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createLocalization } from "@/i18n/init";
import { LocalizationProvider } from "@/i18n/provider";
import { Route as BlobRoute } from "@/routes/ledger.$ledgerOwner.$ledgerName.files.blob.$branch.$";
import { Route as TreeRoute } from "@/routes/ledger.$ledgerOwner.$ledgerName.files.tree.$branch.$";
import { Route as NewRoute } from "@/routes/ledger.$ledgerOwner.$ledgerName.files.new.$branch.$";
import { Route as UploadRoute } from "@/routes/ledger.$ledgerOwner.$ledgerName.files.upload.$branch.$";

vi.unmock("@/common/hooks/use-translations");
vi.unmock("react-i18next");

/**
 * The real Files route options — branch guard, not-found view and head — with
 * only the page bodies and the file read replaced (w4/281).
 */
const routes = [
  { kind: "blob", route: BlobRoute, path: "files/blob/$branch/$" },
  { kind: "tree", route: TreeRoute, path: "files/tree/$branch/$" },
  { kind: "new", route: NewRoute, path: "files/new/$branch/$" },
  { kind: "upload", route: UploadRoute, path: "files/upload/$branch/$" },
] as const;

const fileRead = vi.fn(async () => {});

async function open(url: string) {
  const root = createRootRoute({ component: () => <Outlet /> });
  const children = routes.map(({ kind, route, path }) =>
    createRoute({
      ...(route.options as object),
      getParentRoute: () => root,
      path: `/ledger/$ledgerOwner/$ledgerName/${path}`,
      component: () => <h1>{kind} page</h1>,
      ...(kind === "blob" ? { loader: fileRead } : {}),
    } as never),
  );
  const localization = createLocalization();
  const router = createRouter({
    routeTree: root.addChildren(children),
    context: {
      localization,
      client: new ApolloClient({
        cache: new InMemoryCache(),
        link: ApolloLink.empty(),
      }),
    } as never,
    history: createMemoryHistory({ initialEntries: [url] }),
  });
  await router.load();
  render(
    <LocalizationProvider localization={localization}>
      <RouterProvider router={router} />
    </LocalizationProvider>,
  );
  return router;
}

afterEach(() => {
  cleanup();
  fileRead.mockClear();
});

describe("Files routes for an unsupported branch", () => {
  it.each(routes.map(({ kind }) => kind))(
    "%s answers 404 with a link to main's Files instead of main's content",
    async (kind) => {
      const router = await open(
        `/ledger/open_ledger/example/files/${kind}/qa-20261020-nonexistent-branch/README.md`,
      );

      expect(
        await screen.findByText(
          "Branch “qa-20261020-nonexistent-branch” isn't available here. Files are shown from main.",
        ),
      ).toBeInTheDocument();
      expect(screen.queryByText(`${kind} page`)).toBeNull();
      expect(fileRead).not.toHaveBeenCalled();
      expect(router.state.statusCode).toBe(404);
      expect(
        screen.getByRole("link", { name: "Browse files on main" }),
      ).toHaveAttribute("href", "/ledger/open_ledger/example/files/tree/main");

      const match = router.state.matches.at(-1)!;
      expect(match.status).toBe("notFound");
      const head = (
        routes.find((r) => r.kind === kind)!.route.options.head as (
          args: unknown,
        ) => { links?: unknown[] }
      )({ match, params: match.params, loaderData: undefined });
      expect(head.links ?? []).toEqual([]);
    },
  );

  it.each(routes.map(({ kind }) => kind))(
    "%s still opens on main",
    async (kind) => {
      const router = await open(
        `/ledger/open_ledger/example/files/${kind}/main/README.md`,
      );

      expect(await screen.findByText(`${kind} page`)).toBeInTheDocument();
      expect(router.state.statusCode).toBe(200);
      expect(fileRead.mock.calls.length > 0).toBe(kind === "blob");
    },
  );
});
