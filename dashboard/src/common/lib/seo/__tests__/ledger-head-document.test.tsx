import { act } from "@testing-library/react";
import { renderToString } from "react-dom/server";
import { hydrateRoot } from "react-dom/client";
import {
  createMemoryHistory,
  createRootRouteWithContext,
  createRoute,
  createRouter,
  HeadContent,
  notFound,
  Outlet,
  RouterProvider,
} from "@tanstack/react-router";
import { describe, expect, it, vi } from "vitest";
import { createLocalization } from "@/i18n/init";
import type { RouterContext } from "@/common/types/router-context";
import NotFoundPage from "@/common/root-route/not-found-page";
import { Route as RootRoute } from "@/routes/__root";
import { Route as CatchAllRoute } from "@/routes/$";
import { Route as FilesTreeRoute } from "@/routes/ledger.$ledgerOwner.$ledgerName.files.tree.$branch.$";
import { createLedgerHead } from "../ledger-head";

vi.mock("@/common/root-route/error-page", () => ({ default: () => null }));
vi.mock("@/common/root-route/shell-component", () => ({
  ShellComponent: () => null,
}));
vi.mock("@/common/root-route/root-component", () => ({
  RootComponent: () => null,
}));
vi.mock("@/common/server-fn", () => ({
  fetchUserProfile: vi.fn(async () => ({ status: "signed-out" as const })),
  toAuthContext: () => ({
    userProfile: null,
    authStatus: "signed-out" as const,
  }),
}));
vi.mock("@/i18n/detect-language", () => ({ detectLanguage: () => "en" }));

function testRouter(
  missingLedger = false,
  isServer = false,
  initialEntry = "/ledger/open_ledger/stock-example?time=2026",
) {
  const context: RouterContext = {
    localization: createLocalization(),
    client: {
      readQuery: ({ variables }: { variables: { ledgerId: string } }) => ({
        getLedger: {
          name: variables.ledgerId.split("/")[1],
          private: false,
          description: "An authored portfolio example.",
          options: { title: "Stock & ETF Example" },
        },
      }),
    } as unknown as RouterContext["client"],
  };
  const root = createRootRouteWithContext<RouterContext>()({
    head: RootRoute.options.head,
    notFoundComponent: NotFoundPage,
    shellComponent: ({ children }) => (
      <html lang="en">
        <head>
          <HeadContent />
        </head>
        <body>{children}</body>
      </html>
    ),
    component: Outlet,
  });
  const ledger = createRoute({
    getParentRoute: () => root,
    path: "/ledger/$ledgerOwner/$ledgerName",
    component: Outlet,
    loader: () => {
      if (missingLedger) throw notFound();
    },
  });
  const overview = createRoute({
    getParentRoute: () => ledger,
    path: "/",
    head: (args) => createLedgerHead(args, "ledgerOverview"),
    component: () => <main>Overview</main>,
  });
  const holdings = createRoute({
    getParentRoute: () => ledger,
    path: "holdings",
    head: (args) => createLedgerHead(args, "ledgerHoldings"),
    component: () => <main>Holdings</main>,
  });
  const files = createRoute({
    getParentRoute: () => ledger,
    path: "files/tree/$branch/$",
    head: FilesTreeRoute.options.head,
    component: () => <main>Directory fixture</main>,
  });
  const catchAll = createRoute({
    getParentRoute: () => root,
    path: "$",
    loader: CatchAllRoute.options.loader,
    head: CatchAllRoute.options.head,
    component: NotFoundPage,
  });
  const router = createRouter({
    routeTree: root.addChildren([
      ledger.addChildren([overview, holdings, files]),
      catchAll,
    ]),
    context,
    isServer,
    history: createMemoryHistory({
      initialEntries: [initialEntry],
    }),
  });
  // Start sets this on both server and hydrated client, keeping the outer
  // document outside the client-only root Suspense boundary.
  router.ssr = { manifest: undefined };
  return router;
}

function assertHead(
  doc: Document,
  title: string,
  pathname = "/ledger/open_ledger/stock-example",
) {
  expect(
    [...doc.querySelectorAll("title")].map((node) => node.textContent),
  ).toEqual([title]);
  expect(doc.querySelectorAll('meta[name="description"]')).toHaveLength(1);
  expect(doc.querySelectorAll('meta[property="og:title"]')).toHaveLength(1);
  expect(doc.querySelectorAll('link[rel="canonical"]')).toHaveLength(1);
  expect(doc.querySelector('link[rel="canonical"]')?.getAttribute("href")).toBe(
    `https://beancount.io${pathname}`,
  );
  const alternates = [...doc.querySelectorAll('link[rel="alternate"]')];
  expect(alternates.length).toBeGreaterThan(0);
  for (const alternate of alternates) {
    expect(new URL(alternate.getAttribute("href")!).pathname).toBe(pathname);
  }
}

describe("ledger document head ownership", () => {
  it.each(["", "帳簿/給与 明細"])(
    "renders the actual Files tree route head for path %s in the SSR document",
    async (path) => {
      const pathname = `/ledger/open_ledger/stock-example/files/tree/main${path ? `/${path.split("/").map(encodeURIComponent).join("/")}` : ""}`;
      const router = testRouter(false, true, pathname);
      await router.load();
      expect(router.state.matches.at(-1)?.routeId).toBe(
        "/ledger/$ledgerOwner/$ledgerName/files/tree/$branch/$",
      );
      const html = renderToString(<RouterProvider router={router} />);
      const doc = new DOMParser().parseFromString(html, "text/html");
      const title = path
        ? `${path} · Files - stock-example`
        : "Files - stock-example";
      expect(
        Array.from(doc.querySelectorAll("title"), (node) => node.textContent),
      ).toEqual([title]);
      expect(
        doc.querySelector('meta[property="og:title"]')?.getAttribute("content"),
      ).toBe(title);
      expect(
        doc
          .querySelector('meta[name="twitter:title"]')
          ?.getAttribute("content"),
      ).toBe(title);
      expect(
        doc.querySelector('meta[name="robots"]')?.getAttribute("content"),
      ).toBe("noindex, follow");
      expect(
        doc.querySelectorAll('link[rel="canonical"], link[rel="alternate"]'),
      ).toHaveLength(0);
    },
  );

  it("keeps one title and description through SSR, hydration and report/back navigation", async () => {
    const server = testRouter(false, true);
    await server.load();
    expect(server.state.matches.at(-1)?.pathname).toBe(
      "/ledger/open_ledger/stock-example/",
    );
    const html = renderToString(<RouterProvider router={server} />);
    const parsed = new DOMParser().parseFromString(html, "text/html");
    assertHead(parsed, "Stock & ETF Example");
    const original = document.documentElement.innerHTML;
    const originalLang = document.documentElement.lang;
    document.documentElement.lang = "en";
    document.documentElement.innerHTML = parsed.documentElement.innerHTML;
    const client = testRouter();
    await client.load();
    const recoverable = vi.fn();
    let root: ReturnType<typeof hydrateRoot> | undefined;
    try {
      await act(async () => {
        root = hydrateRoot(document, <RouterProvider router={client} />, {
          onRecoverableError: recoverable,
        });
      });
      assertHead(document, "Stock & ETF Example");
      await act(async () => {
        await client.navigate({
          to: "/ledger/$ledgerOwner/$ledgerName/holdings",
          params: { ledgerOwner: "open_ledger", ledgerName: "stock-example" },
        });
      });
      assertHead(
        document,
        "Holdings - stock-example",
        "/ledger/open_ledger/stock-example/holdings",
      );
      await act(async () => {
        client.history.back();
        await client.load();
      });
      assertHead(document, "Stock & ETF Example");
      expect(recoverable).not.toHaveBeenCalled();
    } finally {
      await act(async () => root?.unmount());
      document.documentElement.innerHTML = original;
      document.documentElement.lang = originalLang;
    }
  });

  it.each([
    [true, "/ledger/open_ledger/stock-example?time=2026"],
    [false, "/missing/%E5%B8%B3%20book/%3F%23?lang=en#section"],
  ] as const)(
    "keeps the exact 404 path in one title through SSR, hydration and navigation (%s, %s)",
    async (missingLedger, initialEntry) => {
      const assertNotFound = (doc: Document, pathname: string) => {
        expect(
          [...doc.querySelectorAll("title")].map((node) => node.textContent),
        ).toEqual([`Page Not Found — ${pathname}`]);
        expect(doc.querySelectorAll('meta[name="description"]')).toHaveLength(
          1,
        );
        expect(
          [...doc.querySelectorAll('meta[name="robots"]')].map((node) =>
            node.getAttribute("content"),
          ),
        ).toEqual(["noindex, follow"]);
        expect(
          doc.querySelectorAll('link[rel="canonical"], link[rel="alternate"]'),
        ).toHaveLength(0);
        expect(
          [...doc.querySelectorAll("h1")].map((node) => node.textContent),
        ).toEqual(["404"]);
      };
      const pathname = initialEntry.split(/[?#]/, 1)[0];
      const server = testRouter(missingLedger, true, initialEntry);
      await server.load();
      expect(server.state.matches[0].globalNotFound).toBe(true);
      const html = renderToString(<RouterProvider router={server} />);
      const parsed = new DOMParser().parseFromString(html, "text/html");
      assertNotFound(parsed, pathname);
      const original = document.documentElement.innerHTML;
      const originalLang = document.documentElement.lang;
      document.documentElement.lang = "en";
      document.documentElement.innerHTML = parsed.documentElement.innerHTML;
      const client = testRouter(missingLedger, false, initialEntry);
      await client.load();
      const recoverable = vi.fn();
      let root: ReturnType<typeof hydrateRoot> | undefined;
      try {
        await act(async () => {
          root = hydrateRoot(document, <RouterProvider router={client} />, {
            onRecoverableError: recoverable,
          });
        });
        assertNotFound(document, pathname);
        await act(async () => {
          await client.navigate({
            to: "/missing/another%20page?lang=en#section",
          });
        });
        assertNotFound(document, "/missing/another%20page");
        expect(recoverable).not.toHaveBeenCalled();
      } finally {
        await act(async () => root?.unmount());
        document.documentElement.innerHTML = original;
        document.documentElement.lang = originalLang;
      }
    },
  );
});
