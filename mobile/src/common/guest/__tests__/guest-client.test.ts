import { gql } from "@apollo/client";
import {
  GetLedgerDirContentDocument,
  GetLedgerFileDocument,
  GetLedgerErrorsDocument,
  GetLedgerEntryContextDocument,
  AccountReportDocument,
  AccountJournalDocument,
  LedgerAccountCloseDatesDocument,
  QueryShellDocument,
  UpdateLedgerFileDocument,
  DeleteLedgerFileDocument,
  CreateLedgerFileDocument,
  DeleteLedgerEntrySourceSliceDocument,
} from "../../../generated-graphql/graphql";
import { createGuestClient } from "../guest-client";

const query = gql`
  query GetLedger($ledgerId: String!) {
    getLedger(ledgerId: $ledgerId) {
      id
      private
    }
  }
`;
const variables = { ledgerId: "open_ledger/example" };
const originalFetch = globalThis.fetch;
let requests: { url: string; options: RequestInit }[];
let response: unknown;
let client: ReturnType<typeof createGuestClient>;
let failures: string[];

beforeEach(() => {
  requests = [];
  failures = [];
  response = {
    data: { getLedger: { id: variables.ledgerId, private: false } },
  };
  globalThis.fetch = async (url, options) => {
    requests.push({ url: String(url), options: options ?? {} });
    return new Response(JSON.stringify(response), {
      headers: { "content-type": "application/json" },
    });
  };
  client = createGuestClient(
    "https://books.example/prefix/",
    "open_ledger/example",
    (failure) => failures.push(failure),
  );
});
afterEach(() => {
  client.stop();
  globalThis.fetch = originalFetch;
});

async function rejects(operation: () => Promise<unknown>) {
  let failed = false;
  try {
    await operation();
  } catch {
    failed = true;
  }
  expect(failed).toBe(true);
}

describe("guest read isolation", () => {
  for (const [name, document, extra, data] of [
    [
      "directory",
      GetLedgerDirContentDocument,
      { dirPath: "" },
      { getLedgerDirContent: [] },
    ],
    [
      "file",
      GetLedgerFileDocument,
      { path: "main.bean" },
      {
        getLedgerFile: {
          content: "",
          encoding: "utf-8",
          name: "main.bean",
          path: "main.bean",
          sha: "sha",
          size: 0,
          type: "file",
        },
      },
    ],
    ["errors", GetLedgerErrorsDocument, {}, { getLedgerErrors: [] }],
    [
      "entry",
      GetLedgerEntryContextDocument,
      { entryHash: "entry" },
      {
        getLedgerEntryContext: {
          slice: "",
          sha256sum: "sha",
          entry: {},
          balances_before: {},
          balances_after: {},
        },
      },
    ],
    [
      "account report",
      AccountReportDocument,
      { accountName: "Assets:Cash", conversion: "units" },
      { getLedgerAccountReport: { linechartData: [], accountBalanceData: [] } },
    ],
    [
      "account journal",
      AccountJournalDocument,
      { query: { account: "Assets:Cash" } },
      {
        getLedgerAccountJournal: {
          account: "Assets:Cash",
          total: 0,
          with_children: true,
          items: [],
        },
      },
    ],
    // w21/635: Accounts and Home hide emptied closed accounts, and Spending stops
    // at today, from these two public reads; the gate refused both for guests.
    [
      "account close dates",
      LedgerAccountCloseDatesDocument,
      {},
      { getLedgerAccountDirectives: [] },
    ],
    [
      "query shell",
      QueryShellDocument,
      { query: "SELECT 1" },
      { queryShell: { table: { rows: [], types: [] } } },
    ],
  ] as const) {
    it(`loads the shared ${name} screen's actual operation anonymously`, async () => {
      response = { data };
      const result = await client.query({
        query: document,
        variables: { ...variables, ...extra },
      });
      expect(result.data).toEqual(data);
      expect(requests.length).toBe(1);
      expect(requests[0].options.credentials).toBe("omit");
      expect(failures).toEqual([]);
    });
  }

  it("blocks the shared file and transaction screens' actual mutations", async () => {
    for (const mutation of [
      UpdateLedgerFileDocument,
      DeleteLedgerFileDocument,
      CreateLedgerFileDocument,
      DeleteLedgerEntrySourceSliceDocument,
    ]) {
      await rejects(() => client.mutate({ mutation, variables }));
    }
    expect(requests.length).toBe(0);
  });

  it("uses only the selected deployment with no credentials or shared cache", async () => {
    await client.query({ query, variables });
    expect(requests[0].url).toBe("https://books.example/prefix/api-gateway/");
    expect(requests[0].options.credentials).toBe("omit");
    expect(new Headers(requests[0].options.headers).has("authorization")).toBe(
      false,
    );
    const other = createGuestClient(
      "https://different.example/",
      "open_ledger/example",
    );
    expect(other.readQuery({ query, variables })).toBe(null);
    other.stop();
  });

  it("blocks account queries, writes, arbitrary ledgers and other example contexts before fetching", async () => {
    await rejects(() =>
      client.query({
        query: gql`
          query ListLedgers {
            listLedgers {
              id
            }
          }
        `,
      }),
    );
    await rejects(() =>
      client.mutate({
        mutation: gql`
          mutation GetLedger($ledgerId: String!) {
            deleteLedger(ledgerId: $ledgerId)
          }
        `,
        variables,
      }),
    );
    await rejects(() =>
      client.query({ query, variables: { ledgerId: "someone/private" } }),
    );
    await rejects(() =>
      client.query({ query, variables: { ledgerId: "open_ledger/nvidia" } }),
    );
    expect(requests.length).toBe(0);
  });

  for (const code of ["FORBIDDEN", "UNAUTHENTICATED", "NOT_FOUND"]) {
    it(`reports ${code} refreshes even when a previous public result was cached`, async () => {
      await client.query({ query, variables });
      response = {
        errors: [{ message: "Example unavailable", extensions: { code } }],
      };
      await rejects(() =>
        client.query({ query, variables, fetchPolicy: "network-only" }),
      );
      expect(failures).toEqual(["unavailable"]);
    });
  }

  // w21/427: a vanished entry is that screen's "removed", not the end of the
  // example. (A missing file is not an error at all: the ledger answers null,
  // so a file read is not exempt, w21/495.)
  for (const [name, document, extra] of [
    ["entry", GetLedgerEntryContextDocument, { entryHash: "gone" }],
  ] as const) {
    it(`leaves a missing ${name} to its own screen`, async () => {
      await client.query({ query, variables });
      response = {
        errors: [{ message: "Not found", extensions: { code: "NOT_FOUND" } }],
      };
      await rejects(() =>
        client.query({
          query: document,
          variables: { ...variables, ...extra },
        }),
      );
      expect(failures).toEqual([]);
    });

    it(`still reports lost access found by the ${name} read`, async () => {
      response = {
        errors: [{ message: "Private", extensions: { code: "FORBIDDEN" } }],
      };
      await rejects(() =>
        client.query({
          query: document,
          variables: { ...variables, ...extra },
        }),
      );
      expect(failures).toEqual(["unavailable"]);
    });
  }

  it("does not exempt a file read: the server never answers it NOT_FOUND", async () => {
    await client.query({ query, variables });
    response = {
      errors: [{ message: "Not found", extensions: { code: "NOT_FOUND" } }],
    };
    await rejects(() =>
      client.query({
        query: GetLedgerFileDocument,
        variables: { ...variables, path: "gone.bean" },
      }),
    );
    expect(failures).toEqual(["unavailable"]);
  });

  it("distinguishes connection failures and never falls back to the managed server", async () => {
    globalThis.fetch = async (url) => {
      requests.push({ url: String(url), options: {} });
      throw new Error("offline");
    };
    await rejects(() => client.query({ query, variables }));
    expect(failures).toEqual(["connection"]);
    expect(requests.map(({ url }) => url)).toEqual([
      "https://books.example/prefix/api-gateway/",
    ]);
  });

  // w21/292: one failed refresh or scroll blanked the whole example though its
  // rows were still on screen.
  it("keeps the example when a connection fails after something loaded", async () => {
    await client.query({ query, variables });
    globalThis.fetch = async () => {
      throw new Error("offline");
    };
    await rejects(() =>
      client.query({ query, variables, fetchPolicy: "network-only" }),
    );
    // A second failing read (a scroll, a pull to refresh) is no different.
    await rejects(() =>
      client.query({ query, variables, fetchPolicy: "network-only" }),
    );
    expect(failures).toEqual([]);
    // The rows are still in the cache for the screens to show.
    const cached = client.readQuery({ query, variables });
    expect(cached?.getLedger.id).toBe(variables.ledgerId);
  });

  it("still blanks it when the first load never arrives", async () => {
    globalThis.fetch = async () => {
      throw new Error("offline");
    };
    await rejects(() => client.query({ query, variables }));
    expect(failures).toEqual(["connection"]);
  });

  it("still reports lost access after a load, and an error result is not a load", async () => {
    response = {
      errors: [
        { message: "Example unavailable", extensions: { code: "NOT_FOUND" } },
      ],
    };
    await rejects(() => client.query({ query, variables }));
    globalThis.fetch = async () => {
      throw new Error("offline");
    };
    await rejects(() =>
      client.query({ query, variables, fetchPolicy: "network-only" }),
    );
    expect(failures).toEqual(["unavailable", "connection"]);
  });

  it("cannot populate a replacement client with a late old response", async () => {
    let release!: (response: Response) => void;
    globalThis.fetch = () =>
      new Promise((resolve) => {
        release = resolve;
      });
    const pending = client.query({ query, variables });
    const replacement = createGuestClient(
      "https://next.example/",
      "open_ledger/example",
    );
    release(
      new Response(JSON.stringify(response), {
        headers: { "content-type": "application/json" },
      }),
    );
    await pending;
    expect(replacement.readQuery({ query, variables })).toBe(null);
    replacement.stop();
  });
});
