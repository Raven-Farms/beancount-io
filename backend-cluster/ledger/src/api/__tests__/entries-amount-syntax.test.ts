import http from "node:http";
import Koa from "koa";
import Router from "@koa/router";
import bodyParser from "koa-bodyparser";
import { setEntriesHandler } from "@/api/entries";
import { restErrorMiddleware } from "@/server/error-middleware";

// The bulk endpoint now checks its projection before committing, the order
// the text-append route uses (w0/m2). The engine's diagnosis is scripted here
// (unit tests are WASM-free); what is under test is the handler: baseline vs
// projection, the refusal envelope, allowInvalid, and that a refusal commits
// nothing.
const MAIN =
  "2026-01-01 open Assets:Cash USD\n2026-01-01 open Equity:Opening\n";
const b64 = (text: string) => Buffer.from(text, "utf8").toString("base64");
const fromB64 = (text: string) => Buffer.from(text, "base64").toString("utf8");

let baselineErrors: {
  message: string;
  source?: { filename: string; lineno: number };
}[] = [];
const committed: { files: { path: string; content: string }[] }[] = [];
// Paths the handler read; a refused amount must not read any file.
const reads: string[] = [];

jest.mock("@/server/auth", () => ({
  authMiddleware: async (_ctx: unknown, next: () => Promise<void>) => next(),
  directiveLimitExempt: () => true,
  giteaClientForRequest: () => ({
    repos: {
      repoGetContents: async (_owner: string, _repo: string, path: string) => {
        reads.push(path);
        if (path !== "main.bean")
          throw Object.assign(new Error("404"), { status: 404 });
        return { data: { content: b64(MAIN), sha: "sha-main" } };
      },
      repoChangeFiles: async (
        _owner: string,
        _repo: string,
        body: { files: { path: string; content: string }[] },
      ) => {
        committed.push(body);
        return { data: {} };
      },
    },
  }),
}));

jest.mock("@/core/directive-limit", () => ({
  checkDirectiveLimitForFileChanges: async () => undefined,
}));

// A stand-in for bean-check: a second `open` of one account is the engine's
// duplicate-open error on the line that repeats it.
function errorsOf(text: string) {
  const seen = new Set<string>();
  const errors = [...baselineErrors];
  text.split("\n").forEach((line, index) => {
    const account = /\bopen (\S+)/.exec(line)?.[1];
    if (!account) return;
    if (seen.has(account)) {
      errors.push({
        message: `Duplicate open directive for ${account}`,
        source: { filename: "main.bean", lineno: index + 1 },
      });
    }
    seen.add(account);
  });
  return errors;
}

jest.mock("../service-context", () => ({
  ...jest.requireActual("../service-context"),
  servicesForRequest: () => ({
    data: {
      getErrors: async () => {
        return errorsOf(MAIN);
      },
      checkProjectedErrors: async ({
        overlays,
      }: {
        overlays: { path: string; content: string }[];
      }) => {
        const main = overlays.find((overlay) => overlay.path === "main.bean");
        return errorsOf(main ? fromB64(main.content) : MAIN);
      },
    },
  }),
}));

async function listen(server: http.Server): Promise<string> {
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  return `http://127.0.0.1:${(server.address() as { port: number }).port}`;
}

describe("bulk entries refuse amounts that are not decimals (w3/641)", () => {
  let server: http.Server;
  let url: string;

  beforeAll(async () => {
    const app = new Koa();
    const router = new Router();
    setEntriesHandler(router);
    app.use(restErrorMiddleware());
    app.use(bodyParser());
    app.use(router.routes());
    server = http.createServer(app.callback());
    url = await listen(server);
  });

  afterAll(() => new Promise<void>((resolve) => server.close(() => resolve())));

  beforeEach(() => {
    baselineErrors = [];
    committed.length = 0;
    reads.length = 0;
  });

  const post = (entries: unknown[]) =>
    fetch(`${url}/entries/alice/books/bulk`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ entries }),
    });
  const transaction = (first: string, second: string) => ({
    type: "transaction",
    item: {
      date: "2026-10-17",
      flag: "*",
      narration: "synthetic",
      postings: [
        { account: "Assets:Cash", units: { number: first, currency: "USD" } },
        {
          account: "Equity:Opening",
          units: { number: second, currency: "USD" },
        },
      ],
    },
  });

  it.each([
    ["(12.50)", "-(12.50)", 'postings[0].units.number "(12.50)"'],
    ["-1,234.56", "1,234.56", 'postings[0].units.number "-1,234.56"'],
    ["12.50", "$-12.50", 'postings[1].units.number "$-12.50"'],
  ])(
    "refuses posting %s / %s as bad input naming the field",
    async (first, second, field) => {
      const response = await post([transaction(first, second)]);
      const body = (await response.json()) as Record<string, any>;

      // A plain refusal: 400, not the 500 a throwing parse became.
      expect(response.status).toBe(400);
      expect(body.error).toBe(`entry 0: ${field} is not a decimal number`);
      expect(reads).toEqual([]);
      expect(committed).toEqual([]);
    },
  );

  it.each([
    [
      "balance",
      {
        date: "2026-09-07",
        account: "Assets:Cash",
        amount: { number: "abc", currency: "USD" },
      },
    ],
    [
      "price",
      {
        date: "2026-09-07",
        currency: "XYZ",
        amount: { number: "1,5", currency: "USD" },
      },
    ],
  ])("refuses a %s amount that is not a number", async (type, item) => {
    const response = await post([{ type, item }]);
    const body = (await response.json()) as Record<string, any>;

    expect(response.status).toBe(400);
    expect(body.error).toMatch(
      /^entry 0: amount\.number ".+" is not a decimal number$/,
    );
    expect(committed).toEqual([]);
  });

  it.each([
    ["-3.21", "3.21"],
    ["1e-7", "-1e-7"],
  ])("still writes %s / %s", async (first, second) => {
    const response = await post([transaction(first, second)]);

    expect(response.status).toBe(200);
    expect(committed).toHaveLength(1);
  });
});
