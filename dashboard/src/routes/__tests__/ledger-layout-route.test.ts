import { CombinedGraphQLErrors } from "@apollo/client/errors";
import { describe, expect, it, vi } from "vitest";
import { isNotFound, isRedirect } from "@tanstack/react-router";
import type { RouterContext } from "@/common/types/router-context";
import { GetLedgerDocument } from "@/graphql/definitions";

vi.mock("@/common/components/ledger-layout", () => ({
  LedgerLayout: () => null,
}));
vi.mock("@/common/components/ledger-layout/ledger-route-error", () => ({
  LedgerRouteError: () => null,
}));

import { Route } from "../ledger.$ledgerOwner.$ledgerName";

type QueryOptions = { query: unknown; variables?: Record<string, unknown> };

function loaderInput(
  query: (options: QueryOptions) => Promise<unknown>,
  href?: string,
) {
  return {
    params: { ledgerOwner: "open_ledger", ledgerName: "example" },
    context: { client: { query } } as unknown as RouterContext,
    // ParsedLocation.href: pathname + search + hash, already assembled by the
    // router and still encoded.
    location: {
      href:
        href ?? "/ledger/open_ledger/example/journal?lang=en&account=Assets",
    },
  };
}

function runLoader(
  query: (options: QueryOptions) => Promise<unknown>,
  href?: string,
) {
  const loader = Route.options.loader as unknown as (
    input: ReturnType<typeof loaderInput>,
  ) => Promise<unknown>;
  return loader(loaderInput(query, href));
}

function graphqlDenied(code: string, message: string) {
  return new CombinedGraphQLErrors({
    errors: [{ message, extensions: { code } }],
  });
}

describe("ledger layout route loader", () => {
  it("awaits only the ledger itself; sidebar counts are owned by their panels", async () => {
    const query = vi.fn(() => Promise.resolve({ data: { getLedger: {} } }));

    await runLoader(query);

    expect(query).toHaveBeenCalledTimes(1);
    expect(query).toHaveBeenCalledWith({
      query: GetLedgerDocument,
      variables: { ledgerId: "open_ledger/example" },
    });
  });

  it("redirects guests to login with the full relative destination before SSR strips Apollo codes", async () => {
    const query = vi.fn(() =>
      Promise.reject(
        graphqlDenied("UNAUTHENTICATED", "Authentication required"),
      ),
    );

    let thrown: unknown;
    try {
      await runLoader(query);
    } catch (error) {
      thrown = error;
    }

    expect(isRedirect(thrown)).toBe(true);
    expect(thrown).toMatchObject({
      options: {
        to: "/auth/login",
        search: {
          next: "/ledger/open_ledger/example/journal?lang=en&account=Assets",
        },
      },
    });
  });

  it("maps authorized denials to not-found so SSR never hydrates a plain Error", async () => {
    const query = vi.fn(() =>
      Promise.reject(graphqlDenied("FORBIDDEN", "Authorization denied")),
    );

    let thrown: unknown;
    try {
      await runLoader(query);
    } catch (error) {
      thrown = error;
    }

    expect(isNotFound(thrown)).toBe(true);
  });

  it("maps missing ledgers to not-found without guessing from message text", async () => {
    const query = vi.fn(() =>
      Promise.reject(graphqlDenied("NOT_FOUND", "Ledger not found")),
    );

    await expect(runLoader(query)).rejects.toSatisfy(isNotFound);
  });

  it("rethrows unexpected failures so the route errorComponent can classify them", async () => {
    const denied = new Error("upstream unavailable");
    const query = vi.fn(() => Promise.reject(denied));

    await expect(runLoader(query)).rejects.toBe(denied);
  });
});

describe("ledger route slugs (w3/628)", () => {
  function run(
    params: { ledgerOwner: string; ledgerName: string },
    href: string,
    query: (options: QueryOptions) => Promise<unknown> = vi.fn(() =>
      Promise.resolve({
        data: { getLedger: { fullName: "open_ledger/example" } },
      }),
    ),
  ) {
    const loader = Route.options.loader as unknown as (input: {
      params: typeof params;
      context: RouterContext;
      location: { href: string };
    }) => Promise<unknown>;
    return loader({
      params,
      context: { client: { query } } as unknown as RouterContext,
      location: { href },
    }).then(
      () => undefined,
      (error: unknown) => error,
    );
  }

  it.each([
    ["Example", "/ledger/open_ledger/Example/journal?time=2026-07#top"],
    ["example.git", "/ledger/open_ledger/example.git/journal?time=2026-07#top"],
  ])(
    "permanently redirects %s to the ledger's URL, keeping path, search and hash",
    async (ledgerName, href) => {
      const query = vi.fn();
      const thrown = await run(
        { ledgerOwner: "open_ledger", ledgerName },
        href,
        query,
      );

      expect(isRedirect(thrown)).toBe(true);
      expect(thrown).toMatchObject({
        options: {
          href: "/ledger/open_ledger/example/journal?time=2026-07#top",
          statusCode: 301,
        },
      });
      expect(query).not.toHaveBeenCalled();
    },
  );

  it.each([["ex/ample"], ["..."], ["a".repeat(101)]])(
    "answers not found for a name no ledger can have: %s",
    async (ledgerName) => {
      const query = vi.fn();
      const thrown = await run(
        { ledgerOwner: "open_ledger", ledgerName },
        `/ledger/open_ledger/${encodeURIComponent(ledgerName)}`,
        query,
      );

      expect(isNotFound(thrown)).toBe(true);
      expect(query).not.toHaveBeenCalled();
    },
  );

  it("answers not found when the API refuses the slug outright", async () => {
    const thrown = await run(
      { ledgerOwner: "open_ledger", ledgerName: "example" },
      "/ledger/open_ledger/example",
      vi.fn(() =>
        Promise.reject(
          graphqlDenied(
            "BAD_USER_INPUT",
            "Ledger name slug must contain 1-100 lowercase letters, digits, underscores, or hyphens",
          ),
        ),
      ),
    );

    expect(isNotFound(thrown)).toBe(true);
  });

  it("redirects an owner spelled in another case to the ledger's own spelling", async () => {
    const thrown = await run(
      { ledgerOwner: "OPEN_LEDGER", ledgerName: "example" },
      "/ledger/OPEN_LEDGER/example/accounts?time=2026",
    );

    expect(thrown).toMatchObject({
      options: {
        href: "/ledger/open_ledger/example/accounts?time=2026",
        statusCode: 301,
      },
    });
  });

  it("loads the canonical spelling without redirecting", async () => {
    expect(
      await run(
        { ledgerOwner: "open_ledger", ledgerName: "example" },
        "/ledger/open_ledger/example",
      ),
    ).toBeUndefined();
  });

  it("leaves a ledger the API resolves under another owner to the API", async () => {
    expect(
      await run(
        { ledgerOwner: "alice", ledgerName: "example" },
        "/ledger/alice/example",
        vi.fn(() =>
          Promise.resolve({ data: { getLedger: { fullName: "bob/example" } } }),
        ),
      ),
    ).toBeUndefined();
  });
});
