// @vitest-environment node
import { describe, expect, it, vi } from "vitest";
import {
  createRequestHandler,
  defaultRenderHandler,
} from "@tanstack/react-router/ssr/server";

// Exercise the production router options and installed router implementation.
// Fixture routes keep authorization, backend requests and file rendering out of
// a regression in URL canonicalization that runs before route loaders.
vi.mock("@/routeTree.gen", async () => {
  const { createElement } = await import("react");
  const { createRootRoute, createRoute, Outlet } = await vi.importActual<
    typeof import("@tanstack/react-router")
  >("@tanstack/react-router");
  const root = createRootRoute({
    component: () =>
      createElement(
        "html",
        null,
        createElement("body", null, createElement(Outlet)),
      ),
    notFoundComponent: () => createElement("p", null, "Fixture not found"),
  });
  const paths = [
    "/ledger/$ledgerOwner/$ledgerName/account/$accountName",
    "/ledger/$ledgerOwner/$ledgerName/entry/$entryHash",
    "/ledger/$ledgerOwner/$ledgerName/commit/$commitSha",
    "/ledger/$ledgerOwner/$ledgerName/files/tree/$branch/$",
    "/ledger/$ledgerOwner/$ledgerName/files/blob/$branch/$",
    "/ledger/$ledgerOwner/$ledgerName",
    "/$username",
  ];
  return {
    routeTree: root.addChildren(
      paths.map((path) =>
        createRoute({
          getParentRoute: () => root,
          path,
          component: () => createElement("p", null, "Fixture route loaded"),
        }),
      ),
    ),
  };
});

vi.mock("@/common/apollo/client", async () => {
  const { ApolloClient, ApolloLink, InMemoryCache } =
    await vi.importActual<typeof import("@apollo/client")>("@apollo/client");
  return {
    getClient: () =>
      new ApolloClient({
        ssrMode: true,
        link: ApolloLink.empty(),
        cache: new InMemoryCache(),
      }),
  };
});

import { getRouter } from "@/router";

const origin = "https://beancount.io";
const ledger = "/ledger/open_ledger/example";
const unsafeCharacters = [
  ["%3C", "<"],
  ["%3E", ">"],
  ["%22", '"'],
  ["%7B", "{"],
  ["%7D", "}"],
  ["%60", "`"],
] as const;

async function serve(path: string) {
  let router!: ReturnType<typeof getRouter>;
  const response = await createRequestHandler({
    request: new Request(new URL(path, origin)),
    createRouter: () => {
      router = getRouter();
      router.update({ isServer: true });
      return router;
    },
  })(defaultRenderHandler);
  const body = await response.text();
  return { response, body, router };
}

async function expectPage(path: string, params: Record<string, string>) {
  const { response, body, router } = await serve(path);
  expect(response.status).toBe(200);
  expect(response.headers.get("Location")).toBeNull();
  expect(body).toContain("Fixture route loaded");
  expect(router.state.matches.at(-1)?.params).toMatchObject(params);
}

describe("encoded paths through the production router's SSR boundary", () => {
  it.each(unsafeCharacters)(
    "serves account names containing %s without a redirect",
    async (encoded, decoded) => {
      await expectPage(`${ledger}/account/Assets:US:a${encoded}b`, {
        ledgerOwner: "open_ledger",
        ledgerName: "example",
        accountName: `Assets:US:a${decoded}b`,
      });
    },
  );

  it.each(unsafeCharacters)(
    "serves file paths containing %s without a redirect",
    async (encoded, decoded) => {
      await expectPage(`${ledger}/files/blob/main/documents/a${encoded}b.pdf`, {
        branch: "main",
        _splat: `documents/a${decoded}b.pdf`,
      });
    },
  );

  it.each<{
    name: string;
    path: string;
    params: Record<string, string>;
  }>([
    {
      name: "entry",
      path: `${ledger}/entry/a%22b`,
      params: { entryHash: 'a"b' },
    },
    {
      name: "commit",
      path: `${ledger}/commit/a%60b`,
      params: { commitSha: "a`b" },
    },
    {
      name: "file tree",
      path: `${ledger}/files/tree/main/a%3Cb`,
      params: { branch: "main", _splat: "a<b" },
    },
    {
      name: "ledger name",
      path: "/ledger/open_ledger/ex%3Cample",
      params: { ledgerOwner: "open_ledger", ledgerName: "ex<ample" },
    },
    {
      name: "profile",
      path: "/u%3Cx",
      params: { username: "u<x" },
    },
    {
      name: "a file named {2026}.pdf",
      path: `${ledger}/files/blob/main/%7B2026%7D.pdf`,
      params: { branch: "main", _splat: "{2026}.pdf" },
    },
  ])("serves the $name route with its decoded parameters", async (entry) => {
    await expectPage(entry.path, entry.params);
  });

  it.each([
    ["space", "a%20b", "a b"],
    ["slash", "a%2Fb", "a/b"],
    ["pipe", "a%7Cb", "a|b"],
    ["caret", "a%5Eb", "a^b"],
    ["backslash", "a%5Cb", "a\\b"],
    ["percent", "a%25b", "a%b"],
    ["Unicode", "Caf%C3%A9", "Café"],
    ["literal encoded less-than", "a%253Cb", "a%3Cb"],
    ["literal encoded slash", "a%252Fb", "a%2Fb"],
  ])("preserves the working %s control", async (_name, encoded, decoded) => {
    await expectPage(`${ledger}/account/${encoded}`, {
      accountName: decoded,
    });
  });

  it("keeps query content separate from path parameters", async () => {
    const { response, router } = await serve(
      `${ledger}/files/blob/main/%7B2026%7D.pdf?note=%3Cnote%3E%22%7B%7D%60&next=%2Fledger%2Fexample`,
    );
    expect(response.status).toBe(200);
    expect(response.headers.get("Location")).toBeNull();
    expect(router.state.matches.at(-1)?.params).toMatchObject({
      _splat: "{2026}.pdf",
    });
    expect(router.state.location.search).toEqual({
      note: '<note>"{}`',
      next: "/ledger/example",
    });
  });

  it("keeps URL-looking parameter values on the requested origin", async () => {
    const { response, router } = await serve(
      `${ledger}/files/blob/main/https%3A%2F%2Fevil.example%2F%7B2026%7D.pdf`,
    );
    expect(response.status).toBe(200);
    expect(response.headers.get("Location")).toBeNull();
    expect(router.state.matches.at(-1)?.params).toMatchObject({
      _splat: "https://evil.example/{2026}.pdf",
    });
    expect(new URL(router.state.location.publicHref, origin).origin).toBe(
      origin,
    );
  });

  it("retains a terminating canonical trailing-slash redirect", async () => {
    const first = await serve(`${ledger}/account/Cash/?q=value`);
    expect(first.response.status).toBe(307);
    const location = first.response.headers.get("Location");
    expect(location).not.toBeNull();
    expect(location).not.toMatch(/[<>"{}`]/);
    const next = new URL(location!, origin);
    expect(next.origin).toBe(origin);
    expect(next.pathname).toBe(`${ledger}/account/Cash`);
    expect(next.searchParams.get("q")).toBe("value");
    const second = await serve(next.href);
    expect(second.response.status).toBe(200);
    expect(second.response.headers.get("Location")).toBeNull();
    expect(second.router.state.location.search).toEqual({ q: "value" });
  });

  it("retains a terminating search normalization redirect", async () => {
    const first = await serve(`${ledger}/account/Cash?q=%22value%22`);
    expect(first.response.status).toBe(307);
    const location = first.response.headers.get("Location");
    expect(location).not.toBeNull();
    const next = new URL(location!, origin);
    expect(next.origin).toBe(origin);
    expect(next.searchParams.get("q")).toBe("value");
    const second = await serve(next.href);
    expect(second.response.status).toBe(200);
    expect(second.response.headers.get("Location")).toBeNull();
    expect(second.router.state.location.search).toEqual({ q: "value" });
  });

  it("returns an honest not-found response for an unknown fixture route", async () => {
    const { response, body } = await serve("/not/a/fixture");
    expect(response.status).toBe(404);
    expect(response.headers.get("Location")).toBeNull();
    expect(body).toContain("Fixture not found");
  });
});
