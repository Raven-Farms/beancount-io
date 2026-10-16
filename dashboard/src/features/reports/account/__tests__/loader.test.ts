import {
  ApolloClient,
  ApolloLink,
  InMemoryCache,
  Observable,
} from "@apollo/client";
import { CombinedGraphQLErrors } from "@apollo/client/errors";
import { describe, expect, it } from "vitest";
import { GetLedgerAccountsDocument } from "@/graphql/definitions";
import { createLocalization } from "@/i18n/init";
import { accountLoader } from "../loader";

const accountNames = [
  "Assets:Bank:Checking",
  "Assets:Closed",
  "Assets:Café%20",
];

function makeClient(
  options: { accounts?: string[]; code?: string; error?: Error } = {},
) {
  const operations: Array<{
    name: string;
    variables: Record<string, unknown>;
  }> = [];
  const client = new ApolloClient({
    cache: new InMemoryCache(),
    link: new ApolloLink(
      (operation) =>
        new Observable((observer) => {
          operations.push({
            name: operation.operationName,
            variables: operation.variables,
          });
          if (options.error) observer.error(options.error);
          else {
            observer.next(
              options.code
                ? {
                    errors: [
                      {
                        message: "Account lookup failed",
                        extensions: { code: options.code },
                      },
                    ],
                  }
                : {
                    data: {
                      getLedgerAccounts: options.accounts ?? accountNames,
                    },
                  },
            );
            observer.complete();
          }
        }),
    ),
  });
  return { client, operations };
}

function input(client: ApolloClient, accountName: string) {
  return {
    params: { ledgerOwner: "alice", ledgerName: "books", accountName },
    context: { client, localization: createLocalization() },
    location: {
      href: "/ledger/alice/books/account/Assets:Missing?time=2025#journal",
    } as Parameters<typeof accountLoader>[0]["location"],
    deps: undefined,
    abortController: new AbortController(),
    preload: false,
    cause: "enter" as const,
  };
}

describe("accountLoader", () => {
  it("loads all account names once and reuses the same cache for open, closed and decoded names", async () => {
    const { client, operations } = makeClient();
    for (const name of accountNames) {
      await expect(accountLoader(input(client, name))).resolves.toEqual({
        accountExists: true,
      });
    }
    expect(operations).toEqual([
      { name: "GetLedgerAccounts", variables: { ledgerId: "alice/books" } },
    ]);
  });

  it("uses the existing sidebar account cache without a request or an open-only status", async () => {
    const { client, operations } = makeClient({
      error: new Error("network must not be needed"),
    });
    client.writeQuery({
      query: GetLedgerAccountsDocument,
      variables: { ledgerId: "alice/books" },
      data: { getLedgerAccounts: accountNames },
    });
    await expect(
      accountLoader(input(client, "Assets:Closed")),
    ).resolves.toEqual({ accountExists: true });
    expect(operations).toEqual([]);
  });

  it.each(["Assets", "Assets:Bank"])(
    "preserves the real aggregate report for known ancestor %s",
    async (name) => {
      const { client } = makeClient();
      await expect(accountLoader(input(client, name))).resolves.toEqual({
        accountExists: true,
      });
    },
  );

  it.each([
    "Assets:Missing",
    "NotARoot:Foo",
    "Assets:Ban",
    "Assets:Bank:",
    "assets:Bank:Checking",
    "Assets:Café ",
  ])(
    "rejects the unknown or partial account name %s without normalizing it",
    async (name) => {
      const { client } = makeClient();
      await expect(accountLoader(input(client, name))).rejects.toMatchObject({
        isNotFound: true,
      });
    },
  );

  it("treats a successful empty accounts list as missing", async () => {
    const { client } = makeClient({ accounts: [] });
    await expect(
      accountLoader(input(client, "Assets:Cash")),
    ).rejects.toMatchObject({ isNotFound: true });
  });

  it("does not reuse another ledger's account inventory", async () => {
    const { client, operations } = makeClient({ accounts: [] });
    client.writeQuery({
      query: GetLedgerAccountsDocument,
      variables: { ledgerId: "alice/other-books" },
      data: { getLedgerAccounts: accountNames },
    });
    await expect(
      accountLoader(input(client, "Assets:Closed")),
    ).rejects.toMatchObject({ isNotFound: true });
    expect(operations).toEqual([
      { name: "GetLedgerAccounts", variables: { ledgerId: "alice/books" } },
    ]);
  });

  it.each(["FORBIDDEN", "NOT_FOUND", "BAD_USER_INPUT"])(
    "maps a known %s query error to not-found",
    async (code) => {
      const { client } = makeClient({ code });
      await expect(
        accountLoader(input(client, "Assets:Cash")),
      ).rejects.toMatchObject({ isNotFound: true });
    },
  );

  it("keeps the full destination when an account read requires login", async () => {
    const { client } = makeClient({ code: "UNAUTHENTICATED" });
    await expect(
      accountLoader(input(client, "Assets:Cash")),
    ).rejects.toMatchObject({
      options: {
        to: "/auth/login",
        search: {
          next: "/ledger/alice/books/account/Assets:Missing?time=2025#journal",
        },
      },
    });
  });

  it("preserves genuine network and unexpected GraphQL failures", async () => {
    const networkError = new Error("Ledger connection failed");
    const { client } = makeClient({ error: networkError });
    await expect(accountLoader(input(client, "Assets:Cash"))).rejects.toBe(
      networkError,
    );
    const graphql = makeClient({ code: "INTERNAL_SERVER_ERROR" });
    await expect(
      accountLoader(input(graphql.client, "Assets:Cash")),
    ).rejects.toBeInstanceOf(CombinedGraphQLErrors);
  });
});
