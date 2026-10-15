import "reflect-metadata";
jest.mock("@ai-sdk/harness/agent", () => ({ HarnessAgent: class {} }));
jest.mock("@ai-sdk/harness-acp", () => ({ createACP: () => ({}) }));

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { buildSchema } from "type-graphql";
import { graphql } from "graphql";
import { LedgerFinanceQueryResolver } from "@/features/ledger/api/resolvers/ledger-finance-resolver.query";
import { LedgerFinanceService } from "@/features/ledger/service/ledger-finance-service";
import { AuthorizationService } from "@/server/api/authorization";
import { graphqlScopeMiddleware } from "@/server/graphql/scope-middleware";
import { assembleMcpRegistry } from "@/server/api/composition-root";
import {
  startV1TestServer,
  pinnedReadToken,
} from "@/server/rest/__tests__/v1-test-server";
import type { IFavaClientFactory } from "@/foundation/clients/fava-client-factory";
import type { AppConfig } from "@/config/config";
import type { AppLayers } from "@/foundation/composition";
import type { McpRequestContext } from "../mcp-context";

/**
 * w6/006. A balance sheet filtered to one transfer has empty aggregates — the
 * net-worth point and the Assets root cancel — while Checking and Savings
 * still hold -500 and 500. The summary took its currency from the request
 * alone, labelled the zeros `units` (or an EUR nothing carried), and dropped
 * both accounts. REST and MCP share the summary seam; GraphQL returns the raw
 * tree, which must not change.
 */

const config = { api: { scopeEnforcement: "enforce" } } as AppConfig;
const filter = 'narration:"Transfer to savings"';

const leaf = (account: string, balance: Record<string, string>) => ({
  account,
  balance,
  balance_children: {},
  children: [],
  has_txns: true,
});
const root = (account: string, children: ReturnType<typeof leaf>[] = []) => ({
  account,
  balance: {},
  balance_children: {},
  children,
  has_txns: false,
});
const transfer = (currency: string) => ({
  net_worth_data: [{ date: "2026-03-31", balance: {} }],
  assets_data: [{ date: "2026-03-31", balance: {} }],
  liabilities_data: [{ date: "2026-03-31", balance: {} }],
  equity_data: [{ date: "2026-03-31", balance: {} }],
  assets_hierarchy_data: root("Assets", [
    leaf("Assets:Bank:Checking", { [currency]: "-500" }),
    leaf("Assets:Bank:Savings", { [currency]: "500" }),
  ]),
  liabilities_hierarchy_data: root("Liabilities"),
  equity_hierarchy_data: root("Equity"),
});
const summary = (currency: string, valuation = "latest-price") => ({
  asOf: "2026-03-31",
  currency,
  valuation,
  assets: 0,
  liabilities: 0,
  equity: 0,
  netWorth: 0,
  byAccount: [
    { account: "Assets:Bank:Checking", balance: -500 },
    { account: "Assets:Bank:Savings", balance: 500 },
  ],
});

let resolver: LedgerFinanceQueryResolver;
let schemaPromise: ReturnType<typeof buildSchema> | undefined;

async function fixture(payload: unknown) {
  const check = jest.fn().mockResolvedValue(true);
  const auth = new AuthorizationService({ check }, jest.fn());
  const getLedgerBalanceSheet = jest
    .fn()
    .mockResolvedValue({ data: { success: true, data: payload } });
  const factory = {
    getPublicApiClient: jest.fn().mockResolvedValue({
      reports: { getLedgerBalanceSheet },
    }),
  };
  const services = {
    ledgerFinance: new LedgerFinanceService(
      factory as unknown as IFavaClientFactory,
      auth,
    ),
  };
  resolver = new LedgerFinanceQueryResolver(services.ledgerFinance);
  schemaPromise ??= buildSchema({
    resolvers: [LedgerFinanceQueryResolver],
    container: { get: () => resolver },
    globalMiddlewares: [graphqlScopeMiddleware("enforce")],
    validate: true,
  });
  const schema = await schemaPromise;
  const rest = await startV1TestServer(
    { services } as unknown as AppLayers,
    config,
    { apiKeys: false },
  );
  rest.setIdentity(pinnedReadToken);
  const server = assembleMcpRegistry(
    { identity: pinnedReadToken, services } as unknown as McpRequestContext,
    config,
  );
  const client = new Client({ name: "balance-summary-parity", version: "1" });
  const [a, b] = InMemoryTransport.createLinkedPair();
  await Promise.all([client.connect(a), server.connect(b)]);
  const path = (query: Record<string, string>) =>
    `statements/balance-sheet?${new URLSearchParams({ filter, ...query })}`;
  return {
    getLedgerBalanceSheet,
    /** The REST and MCP answers, asserted equal before either is returned. */
    read: async (query: Record<string, string>) => {
      const response = await fetch(
        `${rest.url}/api-gateway/v1/ledgers/alice/main/${path(query)}`,
      );
      expect(response.status).toBe(200);
      const result = await client.readResource({
        uri: `beancount://alice/main/${path(query)}`,
      });
      const content = result.contents[0];
      if (!("text" in content)) throw new Error("Expected JSON resource");
      const mcp = JSON.parse(content.text);
      expect(await response.json()).toEqual(mcp);
      return mcp;
    },
    gql: (conversion: string) =>
      graphql({
        schema,
        source: `query($filter: String, $conversion: String) {
          getLedgerBalanceSheet(ledgerId: "alice/main", filter: $filter, conversion: $conversion) {
            netWorthData { date balance }
            assetsHierarchyData { account balance balanceChildren children }
          }
        }`,
        variableValues: { filter, conversion },
        contextValue: { identity: pinnedReadToken },
      }),
    close: async () => {
      await client.close();
      await server.close();
      await rest.close();
    },
  };
}

describe("balance-sheet summary of a cancelling transfer (w6/006)", () => {
  it.each([
    ["units", "units"],
    ["at_cost", "cost"],
    ["at_value", "latest-price"],
    ["USD", "latest-price"],
  ])(
    "keeps both signed accounts with conversion=%s",
    async (conversion, valuation) => {
      const f = await fixture(transfer("USD"));
      try {
        expect(await f.read({ conversion })).toEqual(summary("USD", valuation));
        // The filter and conversion reach the ledger unchanged.
        for (const [, , query] of f.getLedgerBalanceSheet.mock.calls)
          expect(query).toMatchObject({ filter, conversion });
      } finally {
        await f.close();
      }
    },
  );

  it("reports USD rows when the request names an EUR nothing carries", async () => {
    const f = await fixture(transfer("USD"));
    try {
      expect(await f.read({ conversion: "EUR" })).toEqual(summary("USD"));
    } finally {
      await f.close();
    }
  });

  it("reads a non-USD ledger's currency from its accounts", async () => {
    const f = await fixture(transfer("CHF"));
    try {
      expect(await f.read({ conversion: "units" })).toEqual(
        summary("CHF", "units"),
      );
    } finally {
      await f.close();
    }
  });

  it("answers a truly empty sheet in the default currency, not a strategy", async () => {
    const f = await fixture({
      ...transfer("USD"),
      assets_hierarchy_data: root("Assets"),
    });
    try {
      expect(await f.read({ conversion: "at_value" })).toEqual({
        ...summary("USD"),
        byAccount: [],
      });
    } finally {
      await f.close();
    }
  });

  it("keeps nonzero and mixed-currency aggregates on their existing policy", async () => {
    const f = await fixture({
      ...transfer("USD"),
      net_worth_data: [
        { date: "2026-03-31", balance: { USD: "900", EUR: "40" } },
      ],
      assets_hierarchy_data: {
        ...root("Assets", [
          leaf("Assets:Bank:Checking", { EUR: "40", USD: "100" }),
          leaf("Assets:Bank:Savings", { USD: "800" }),
        ]),
        // USD is seen first, so it wins the existing tie with EUR.
        balance_children: { USD: "900", EUR: "40" },
      },
    });
    try {
      expect(await f.read({ conversion: "EUR" })).toEqual({
        ...summary("EUR"),
        assets: 40,
        netWorth: 40,
        byAccount: [{ account: "Assets:Bank:Checking", balance: 40 }],
      });
      expect(await f.read({ conversion: "units" })).toMatchObject({
        currency: "USD",
        assets: 900,
        netWorth: 900,
      });
    } finally {
      await f.close();
    }
  });

  it.each(["units", "EUR"])(
    "leaves the raw and GraphQL payloads untouched with conversion=%s",
    async (conversion) => {
      const payload = transfer("USD");
      const f = await fixture(payload);
      try {
        expect(await f.read({ conversion, shape: "fava" })).toEqual(payload);
        const gql = await f.gql(conversion);
        expect(gql.errors).toBeUndefined();
        expect(gql.data?.getLedgerBalanceSheet).toEqual({
          netWorthData: payload.net_worth_data,
          assetsHierarchyData: {
            account: "Assets",
            balance: {},
            balanceChildren: {},
            // The JSON children keep GraphQL's existing camel-case mapping.
            children: payload.assets_hierarchy_data.children.map((child) => ({
              account: child.account,
              balance: child.balance,
              balanceChildren: child.balance_children,
              children: [],
              hasTxns: child.has_txns,
            })),
          },
        });
      } finally {
        await f.close();
      }
    },
  );
});

/**
 * w6/009. The ledger values each net-worth series point at its interval end
 * but every account tree at the latest price. A historical window therefore
 * returns two snapshots, and the summary took net worth from one and assets
 * from the other: January's 2 XYZ (priced 10 then, 20 now) read as assets 40
 * beside a net worth of 5. Net worth now comes from the same trees as every
 * other number, and the summary says which valuation that is.
 */
describe("balance-sheet summary valuation basis (w6/009)", () => {
  const sheet = (
    broker: Record<string, string>,
    card: Record<string, string>,
    netWorthPoint: Record<string, string>,
  ) => ({
    ...transfer("USD"),
    net_worth_data: [{ date: "2026-01-31", balance: netWorthPoint }],
    assets_hierarchy_data: {
      ...root("Assets", [leaf("Assets:Broker", broker)]),
      balance_children: broker,
    },
    liabilities_hierarchy_data: {
      ...root("Liabilities", [leaf("Liabilities:Card", card)]),
      balance_children: card,
    },
  });
  // January's series point values 2 XYZ at January's 10 USD; the trees value
  // them at the latest 20 USD.
  const historical = sheet({ USD: "40" }, { USD: "-15" }, { USD: "5" });

  it("derives net worth from the reported accounts, not the dated series point", async () => {
    const f = await fixture(historical);
    try {
      const summary = await f.read({ conversion: "USD", time: "2026-01" });
      expect(summary).toEqual({
        asOf: "2026-01-31",
        currency: "USD",
        valuation: "latest-price",
        assets: 40,
        liabilities: -15,
        equity: 0,
        netWorth: 25,
        byAccount: [
          { account: "Assets:Broker", balance: 40 },
          { account: "Liabilities:Card", balance: -15 },
        ],
      });
      // The rows sum to the totals they sit under.
      const rows = summary.byAccount.reduce(
        (sum: number, row: { balance: number }) => sum + row.balance,
        0,
      );
      expect(rows).toBe(summary.netWorth);
    } finally {
      await f.close();
    }
  });

  it.each([
    {
      conversion: "at_cost",
      // Booked cost is undated, so the series point and the trees agree.
      payload: sheet({ USD: "20" }, { USD: "-15" }, { USD: "5" }),
      expected: { valuation: "cost", currency: "USD", netWorth: 5 },
    },
    {
      conversion: "units",
      payload: sheet({ XYZ: "2" }, { USD: "-15" }, { XYZ: "2", USD: "-15" }),
      expected: { valuation: "units", currency: "XYZ", netWorth: 2 },
    },
    {
      // Unfiltered: the last series point is valued at the latest price too.
      conversion: "USD",
      payload: sheet({ USD: "40" }, { USD: "-15" }, { USD: "25" }),
      expected: { valuation: "latest-price", currency: "USD", netWorth: 25 },
    },
  ])(
    "keeps the identity and labels $conversion as $expected.valuation",
    async ({ conversion, payload, expected }) => {
      const f = await fixture(payload);
      try {
        const summary = await f.read({ conversion });
        expect(summary).toMatchObject(expected);
        expect(summary.netWorth).toBe(summary.assets + summary.liabilities);
      } finally {
        await f.close();
      }
    },
  );

  it("leaves both raw views as the ledger sent them", async () => {
    const f = await fixture(historical);
    try {
      expect(
        await f.read({ conversion: "USD", time: "2026-01", shape: "fava" }),
      ).toEqual(historical);
      const gql = await f.gql("USD");
      expect(gql.errors).toBeUndefined();
      expect(
        (gql.data?.getLedgerBalanceSheet as { netWorthData: unknown })
          .netWorthData,
      ).toEqual([{ date: "2026-01-31", balance: { USD: "5" } }]);
    } finally {
      await f.close();
    }
  });
});
