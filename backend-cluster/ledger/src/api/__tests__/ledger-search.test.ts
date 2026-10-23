import http from "node:http";
import Koa from "koa";
import Router from "@koa/router";
import { config } from "@/config";
import { setLedgersHandler } from "@/api/ledgers";
import { restErrorMiddleware } from "@/server/error-middleware";
import { clearMemoizedGiteaClients } from "@/features/gitea/service/gitea-client-factory";
import {
  mightBeOwnerName,
  normalizeSearchText,
  repoMatchesTerm,
  searchTerms,
} from "@/api/ledger-search";

const AUTH = `Basic ${Buffer.from("alice:synthetic-password").toString("base64")}`;

type Repo = {
  id: number;
  name: string;
  full_name: string;
  owner: number;
  description: string;
};

const repo = (
  id: number,
  owner: string,
  ownerId: number,
  name: string,
  description = "",
): Repo => ({
  id,
  name,
  full_name: `${owner}/${name}`,
  owner: ownerId,
  description,
});

// Gitea, reduced to the rule that matters here: `q` is ONE substring of the
// repository name (or, with includeDesc, its description), and `uid` limits the
// search to one owner.
const REPOS = [
  repo(1, "open_ledger", 7, "crypto-example", "Crypto sample"),
  repo(2, "open_ledger", 7, "kroger", "Groceries"),
  repo(3, "open_ledger", 7, "stocks-example", "Stocks sample"),
  repo(4, "alice", 1, "my-book", "Household budget"),
  repo(5, "bob", 2, "example-ledger", "Work"),
  repo(6, "elsewhere", 9, "demo", "A demo of open_ledger"),
];
const OWNERS: Record<string, number> = { open_ledger: 7, alice: 1, bob: 2 };

function wire(r: Repo): Record<string, unknown> {
  return {
    id: r.id,
    name: r.name,
    full_name: r.full_name,
    private: false,
    empty: false,
    size: 1,
    description: r.description,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-02T00:00:00Z",
    permissions: null,
  };
}

async function listen(server: http.Server): Promise<string> {
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  return `http://127.0.0.1:${(server.address() as { port: number }).port}`;
}

describe("GET /ledgers/search reads the query as words (w21/245)", () => {
  const upstreamCalls: string[] = [];
  let upstream: http.Server;
  let ledgerServer: http.Server;
  let ledgerUrl: string;
  const originalGiteaUrl = config.gitea.baseUrl;

  beforeAll(async () => {
    upstream = http.createServer((request, response) => {
      const url = new URL(request.url!, "http://upstream");
      upstreamCalls.push(`${url.pathname}${url.search}`);
      const send = (status: number, data: unknown) => {
        response.writeHead(status, { "content-type": "application/json" });
        response.end(JSON.stringify(data));
      };
      const user = /^\/api\/v1\/users\/([^/]+)$/.exec(url.pathname);
      if (user) {
        const id = OWNERS[decodeURIComponent(user[1])];
        return id === undefined
          ? send(404, { message: "user does not exist" })
          : send(200, { id, login: user[1] });
      }
      if (url.pathname === "/api/v1/repos/search") {
        const q = (url.searchParams.get("q") ?? "").toLowerCase();
        const uid = url.searchParams.get("uid");
        const desc = url.searchParams.get("includeDesc") === "true";
        const page = Number(url.searchParams.get("page") ?? "1");
        const limit = Number(url.searchParams.get("limit") ?? "20");
        const found = REPOS.filter(
          (r) =>
            (uid === null || r.owner === Number(uid)) &&
            (!q ||
              r.name.toLowerCase().includes(q) ||
              (desc && r.description.toLowerCase().includes(q))),
        );
        return send(200, {
          ok: true,
          data: found.slice((page - 1) * limit, page * limit).map(wire),
        });
      }
      return send(500, { message: `Unexpected: ${request.url}` });
    });
    config.gitea.baseUrl = await listen(upstream);
    clearMemoizedGiteaClients();
    const app = new Koa();
    const router = new Router();
    setLedgersHandler(router);
    app.use(restErrorMiddleware()).use(router.routes());
    ledgerServer = http.createServer(app.callback());
    ledgerUrl = await listen(ledgerServer);
  });

  beforeEach(() => {
    upstreamCalls.length = 0;
  });

  afterAll(async () => {
    await Promise.all(
      [ledgerServer, upstream].map(
        (server) =>
          new Promise<void>((resolve) => server.close(() => resolve())),
      ),
    );
    config.gitea.baseUrl = originalGiteaUrl;
    clearMemoizedGiteaClients();
  });

  const search = async (query: string): Promise<string[]> => {
    const response = await fetch(`${ledgerUrl}/ledgers/search?${query}`, {
      headers: { authorization: AUTH },
      signal: AbortSignal.timeout(5000),
    });
    expect(response.status).toBe(200);
    const body = (await response.json()) as {
      data: { data: { full_name: string }[] };
    };
    return body.data.data.map((r) => r.full_name);
  };

  it("finds crypto-example for the words 'crypto example'", async () => {
    expect(await search("q=crypto%20example&include_desc=true")).toEqual([
      "open_ledger/crypto-example",
    ]);
  });

  it("lists an owner's ledgers, then ledgers that merely mention it", async () => {
    expect(await search("q=open_ledger&include_desc=true")).toEqual([
      "elsewhere/demo",
      "open_ledger/crypto-example",
      "open_ledger/kroger",
      "open_ledger/stocks-example",
    ]);
  });

  it("narrows an owner's ledgers by another word", async () => {
    expect(await search("q=open_ledger%20crypto&include_desc=true")).toEqual([
      "open_ledger/crypto-example",
    ]);
  });

  it("needs every word", async () => {
    expect(await search("q=crypto%20household&include_desc=true")).toEqual([]);
  });

  it("pages the matches, not Gitea's pages", async () => {
    const first = await search(
      "q=open_ledger&include_desc=true&limit=2&page=1",
    );
    const second = await search(
      "q=open_ledger&include_desc=true&limit=2&page=2",
    );
    expect(first).toEqual(["elsewhere/demo", "open_ledger/crypto-example"]);
    expect(second).toEqual([
      "open_ledger/kroger",
      "open_ledger/stocks-example",
    ]);
    expect(
      await search("q=open_ledger&include_desc=true&limit=2&page=3"),
    ).toEqual([]);
  });

  it("leaves a single word that names no owner to Gitea, as before", async () => {
    expect(await search("q=example")).toEqual([
      "open_ledger/crypto-example",
      "open_ledger/stocks-example",
      "bob/example-ledger",
    ]);
    expect(await search("q=crypto")).toEqual(["open_ledger/crypto-example"]);
  });

  it("does not expand an owner the caller already pinned with uid", async () => {
    expect(await search("q=open_ledger&uid=7")).toEqual([]);
    expect(
      upstreamCalls.some((call) => call.startsWith("/api/v1/users/")),
    ).toBe(false);
  });

  it("passes an empty query straight through", async () => {
    expect((await search("limit=3")).length).toBe(3);
    expect(await search("q=%20%20&limit=2")).toEqual([
      "open_ledger/crypto-example",
      "open_ledger/kroger",
    ]);
  });
});

describe("ledger search words", () => {
  it("splits a query into words and reads hyphens as breaks", () => {
    expect(searchTerms("  crypto   example ")).toEqual(["crypto", "example"]);
    expect(searchTerms(undefined)).toEqual([]);
    expect(normalizeSearchText("Open_Ledger/Crypto-Example")).toBe(
      "open ledger crypto example",
    );
    expect(
      repoMatchesTerm(
        { full_name: "open_ledger/crypto-example" },
        "ledger crypto",
      ),
    ).toBe(true);
    expect(
      repoMatchesTerm({ full_name: "a/b", description: "Household" }, "house"),
    ).toBe(true);
    expect(repoMatchesTerm({ full_name: "a/b" }, "zzz")).toBe(false);
  });

  it("only looks up words that can be an owner name", () => {
    expect(mightBeOwnerName("open_ledger")).toBe(true);
    expect(mightBeOwnerName("a/b")).toBe(false);
    expect(mightBeOwnerName("-x")).toBe(false);
    expect(mightBeOwnerName("a".repeat(40))).toBe(false);
  });
});
